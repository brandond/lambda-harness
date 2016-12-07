from __future__ import print_function
from _multiprocessing import Connection
import sys
import os

try:
    socket_fd = int(os.environ['_LAMBDA_CONTROL_SOCKET'])
    socket = Connection(handle=socket_fd, readable=True, writable=True)
except KeyError as e:
    raise RuntimeError('Could not connect to control socket - environment configuration not present')

def receive_start():
    return socket.recv().get('args', [])

def report_running(invokeid):
    socket.send({'name': 'running', 'args': [invokeid]})

def receive_invoke():
    return socket.recv().get('args', [])

def report_fault(invokeid, msg, except_value=None, trace=None):
    return socket.send({'name': 'fault', 'args': [invokeid, msg, except_value, trace]})

def report_done(invokeid, errortype=None, result=None):
    return socket.send({'name': 'done', 'args': [invokeid, errortype, result]})

def send_console_message(msg):
    return socket.send({'name': 'console', 'args': [msg]})

def log_bytes(msg, fileno):
    return socket.send({'name': 'log', 'args': [msg, fileno]})

def get_remaining_time():
    socket.send({'name': 'remaining'})
    return socket.recv().get('args', 0.0)
