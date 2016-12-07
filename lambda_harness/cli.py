from __future__ import print_function
from awscli.paramfile import get_paramfile, ResourceLoadingError
from pprint import pprint
from .extractor import Extractor
from .slicer import Slicer
import click
import json
import time
import imp
import sys
import os
import re
import io

VARIABLE_VAL_PATTERN = '[^,]*'
VARIABLE_KEY_PATTERN = '[a-zA-Z]([a-zA-Z0-9_])+'
VARIABLE_KEY_RESERVE = ['LAMBDA_TASK_ROOT', 'LAMBDA_RUNTIME_DIR',
                        'AWS_REGION', 'AWS_DEFAULT_REGION',
                        'AWS_LAMBDA_LOG_GROUP_NAME', 'AWS_LAMBDA_LOG_STREAM_NAME',
                        'AWS_LAMBDA_FUNCTION_NAME',
                        'AWS_LAMBDA_FUNCTION_MEMORY_SIZE', 'AWS_LAMBDA_FUNCTION_VERSION',
                        'AWS_ACCESS_KEY', 'AWS__ACCESS_KEY_ID',
                        'AWS_SECRET__KEY', 'AWS_SECRET_ACCESS_KEY',
                        'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN']

def validate_variables(variables):
    reserved_keys = []
    if not isinstance(variables, dict):
        raise click.exceptions.ClickException("Invalid type for variables, value: {0}, type: {1}, valid types: {2}"
                                              .format(variables, type(variables), dict))

    for (key, val) in variables.items():
        if not isinstance(val, basestring):
            raise click.exceptions.ClickException("Invalid type for variables.{0}, value: {1}, type: {2}, valid types: {3}"
                                                  .format(key, val, type(val), basestring))
        elif not re.match(VARIABLE_KEY_PATTERN, key):
            raise click.exceptions.ClickException("variables failed to satisfy constraint: "
                                                  "Map keys must satisfy constraint: [Member must satisfy regular expression pattern: {0}]"
                                                  .format(VARIABLE_KEY_PATTERN))
        elif not re.match(VARIABLE_VAL_PATTERN, val):
            raise click.exceptions.ClickException("variables failed to satisfy constraint: "
                                                  "Map values must satisfy constraint: [Member must satisfy regular expression pattern: {0}]"
                                                  .format(VARIABLE_VAL_PATTERN))
        elif key in VARIABLE_KEY_RESERVE:
            reserved_keys.append(key)

    if reserved_keys:
        raise click.exceptions.ClickException("variables provided contain reserved keys that are currently not supported for modification. "
                                              "Reserved keys used in this request: {0}"
                                              .format(', '.join(reserved_keys)))

def try_get_paramfile(ctx, param, value):
    if value is not None:
        try:
            new_value = get_paramfile(value)
            if new_value is not None:
                value = new_value
        except ResourceLoadingError as e:
            raise click.BadParameter(e.message)
    return value

def print_var(result):
    tty = sys.stdout.isatty()
    if tty:
        sys.stdout.write('\033[1m')
        sys.stdout.flush()

    if isinstance(result, basestring):
        print(result)
    else:
        pprint(result)

    if tty:
        sys.stdout.write('\033[0m')
        sys.stdout.flush()

@click.group()
def cli():
    pass

@cli.command()
@click.option('--path', required=True, type=click.Path(exists=True), help='The path to your Python Lambda function and configuration')
@click.option('--payload', default='{}', help='JSON that you want to provide to your Lambda function as input.', callback=try_get_paramfile)
@click.option('--client-context', default='', help='Client-specific information as base64-encoded JSON.', callback=try_get_paramfile)
@click.option('--variables', default=None, help='JSON runtime environment variables. Overrides config settings.')
@click.option('--qualifier', default='$LATEST', help='Lambda function version or alias name.')
@click.option('--profile', default=None, help='Use a specific profile from your credential file.')
@click.option('--region', default=None, help='The region to use. Overrides config/env settings.')
@click.option('--interval', default=0, help='Inverval in milliseconds between invocations.')
def invoke(path, payload, client_context, variables, qualifier, profile, region, interval):
    module_path = os.path.dirname(__file__)
    for module_file in ('bootstrap.py', 'wsgi.py'):
        if os.path.getsize(os.path.join(module_path, 'awslambda', module_file)) < 512:
            raise click.exceptions.ClickException('AWS Lambda code is not available. Please run "lambda bootstrap"')
    try:
        with open(os.path.join(path, 'lambda.json'), 'r') as json_file:
            lambda_config = json.load(json_file)
    except IOError as e:
        raise click.exceptions.FileError(filename=e.filename, hint=e.strerror)

    lambda_name = lambda_config.get('name')
    lambda_memory = str(lambda_config.get('memory'))
    lambda_timeout = int(lambda_config.get('timeout'))
    lambda_handler = lambda_config.get('handler')
    lambda_version = qualifier
    lambda_region = lambda_config.get('region') if region is None else region
    lambda_variables = lambda_config.get('variables', {}) if variables is None else json.loads(variables)

    validate_variables(lambda_variables)

    events = io.BytesIO(payload.encode())
    contexts = io.BytesIO(client_context.encode())

    first_invoke = True
    slicer = Slicer(profile, path, lambda_name, lambda_handler, lambda_version, lambda_memory, lambda_timeout, lambda_region, lambda_variables)
    while True:
        event = events.readline()
        context = contexts.readline()
        if event:
            if first_invoke:
                first_invoke = False
            else:
                time.sleep(interval / 1000.0)

            print_var(slicer.invoke(event, context))
        else:
            break

@cli.command()
@click.option('--profile', default=None, help='Use a specific profile from your credential file.')
@click.option('--region', default=None, help='The region to use. Overrides config/env settings.')
@click.option('--cleanup/--no-cleanup', default=True, help='Do not remove bootstrap role and lambda after code extraction')
def bootstrap(profile, region, cleanup):
    Extractor(profile, region, cleanup).extract()
