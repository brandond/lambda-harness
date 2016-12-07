from __future__ import print_function
from awscli.paramfile import get_paramfile, ResourceLoadingError
from pprint import pprint
from .extractor import Extractor
from .slicer import Slicer
import click
import json
import imp
import sys
import os
import io

def try_get_paramfile(ctx, param, value):
    if value is not None:
        try:
            new_value = get_paramfile(value)
            if new_value is not None:
                value = new_value
        except ResourceLoadingError as e:
            raise click.BadParameter(e.message)
    return value

@click.group()
def cli():
    pass

@cli.command()
@click.option('--path', required=True, type=click.Path(exists=True), help='The path to your Python Lambda function and configuration')
@click.option('--payload', default='{}', help='JSON that you want to provide to your Lambda function as input.', callback=try_get_paramfile)
@click.option('--client-context', default='', help='Client-specific information as base64-encoded JSON.', callback=try_get_paramfile)
@click.option('--qualifier', default='$LATEST', help='Lambda function version or alias name.')
@click.option('--profile', default=None, help='Use a specific profile from your credential file.')
@click.option('--region', default=None, help='The region to use. Overrides config/env settings.')
def invoke(path, payload, client_context, qualifier, profile, region):

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

    events = io.BytesIO(payload.encode())
    contexts = io.BytesIO(client_context.encode())

    slicer = Slicer(profile, path, lambda_name, lambda_handler, lambda_version, lambda_memory, lambda_timeout, lambda_region)
    while True:
        event = events.readline()
        context = contexts.readline()
        if event:
            result = slicer.invoke(event, context)
            if sys.stdout.isatty():
                sys.stdout.write('\033[1m')
            if isinstance(result, basestring):
                print(result)
            else:
                pprint(result)
            if sys.stdout.isatty():
                sys.stdout.write('\033[0m')
        else:
            break

@cli.command()
@click.option('--profile', default=None, help='Use a specific profile from your credential file.')
@click.option('--region', default=None, help='The region to use. Overrides config/env settings.')
@click.option('--cleanup/--no-cleanup', default=True, help='Do not remove bootstrap role and lambda after code extraction')
def bootstrap(profile, region, cleanup):
    Extractor(profile, region, cleanup).extract()
