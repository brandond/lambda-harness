from __future__ import print_function
from _multiprocessing import Connection
import botocore.handlers
from requests import Response
import json
import sys
import os

def receive_start():
    return socket.recv().get('args', [])

def report_user_init_start():
    return socket.send({'name': 'user_init_start'})

def report_user_init_end():
    return socket.send({'name': 'user_init_end'})

def report_running(invokeid):
    return socket.send({'name': 'running', 'args': [invokeid]})

def receive_invoke():
    return socket.recv().get('args', [])

def report_user_invoke_start():
    return socket.send({'name': 'user_invoke_start'})

def report_user_invoke_end():
    return socket.send({'name': 'user_invoke_end'})

def report_fault(invokeid, msg, except_value=None, trace=None):
    return socket.send({'name': 'fault', 'args': [invokeid, msg, except_value, trace]})

def report_xray_exception(xray_json):
    return socket.send({'name': 'xray_exception', 'args': [xray_json]})

def report_done(invokeid, errortype=None, result=None):
    return socket.send({'name': 'done', 'args': [invokeid, errortype, result]})

def send_console_message(msg, length=0):
    return socket.send({'name': 'console', 'args': [msg]})

def log_bytes(msg, fileno):
    return socket.send({'name': 'log', 'args': [msg, fileno]})

def get_remaining_time():
    socket.send({'name': 'remaining'})
    return socket.recv().get('args', 0.0)

def log_sb(msg):
    return log_bytes(msg+"\n", 0)

def _lambda_invoke_hook(*args, **kwargs):
    function_name = kwargs['params']['url_path'].split('/')[3]

    if function_name == os.environ['AWS_LAMBDA_FUNCTION_NAME']:
        qualifier = kwargs['params']['query_string'].get('Qualifier', '$LATEST')
        context = kwargs['params']['headers'].get('X-Amz-Client-Context', '')
        type = kwargs['params']['headers'].get('X-Amz-Invocation-Type', 'Event')
        body = kwargs['params']['body']

        socket.send({'name': 'invoke', 'args': [type, context, body, qualifier]})
        return socket.recv().get('args')

try:
    socket_fd = int(os.environ['_LAMBDA_CONTROL_SOCKET'])
    socket = Connection(handle=socket_fd, readable=True, writable=True)
except KeyError as e:
    raise RuntimeError('Could not connect to control socket - environment configuration not present')

botocore.handlers.BUILTIN_HANDLERS.append(('before-call.lambda.Invoke', _lambda_invoke_hook))
