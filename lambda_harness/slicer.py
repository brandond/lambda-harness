from __future__ import print_function
from multiprocessing import Process, Pipe
from datetime import datetime
import atexit
import base64
import boto3
import time
import json
import uuid
import math
import sys
import os

# Call flow:
#   Bootstrap init, call recv_start()
#   Bootstrap loads module specified by receive_start return values
#   Bootstrap calls module.init()
#   Bootstrap calls report_done (or report_fault if init returns wsgi.FaultException)
#   Bootstrap enters loop:
#     Bootstrap calls receive_invoke()
#     Bootstrap sets up environment as specified by wait_for_invoke return values
#     Bootstrap calls handle_http_request or handle_event_request
#     Handle calls module.request_handler
#     Handle calls report_fault if exceptions thrown
#     Handle calls report_done
#
# Note that the sandbox cgroup is frozen after report_done is called and not thawed until
# new invoke request is waiting. Any proceses active during this time will be suspended.
#
# It appears that the START line is logged as soon as the runtime is ready to invoke the handler,
# as it seems to be triggered by the init calling report_done - regardless of whether or not the
# bootstrap code ever calls receive_invoke. 

class Slicer(object):
    __slots__ = ('session',
                 'account_id',
                 'sandbox_id',
                 'invoke_id',
                 'path',
                 'name',
                 'handler',
                 'version',
                 'memory',
                 'timeout',
                 'variables',
                 'control_socket',
                 'console_socket',
                 'sandbox_process',
                 'state',
                 'result',
                 'start_time'
                )

    def make_context(self, context):
        return {'cognito_identity_id': None, 'cognito_identity_pool_id': None, 'client_context': base64.b64decode(context) if context else None}

    def __init__(self, profile, path, name, handler, version, memory, timeout, region, variables):
        self.session = boto3.session.Session(profile_name=profile, region_name=region)
        self.account_id = self.session.client('sts').get_caller_identity().get('Account') 
        self.path = os.path.abspath(path)
        self.name = name
        self.handler = handler
        self.version = version
        self.memory = memory
        self.timeout = timeout
        self.variables = variables
        self.sandbox_id = str(uuid.uuid4()).replace('-','')
        self.invoke_id = str(uuid.uuid4())
        self.control_socket = None
        self.console_socket = None
        self.sandbox_process = None
        self.state = 'Uninitialized'
        self.result = None
        self.start_time = None
        atexit.register(self.terminate_sandbox)

    def start_sandbox(self):
        self.start_time = datetime.now()
        if self.sandbox_process != None:
            return

        self.control_socket, child_control = Pipe()
        self.console_socket, child_console = Pipe()
        self.sandbox_process = Process(target=self.start_bootstrap, args=(child_control,child_console))
        print("<CREATE Id:%s>" %(self.sandbox_id), file=sys.stderr)
       
        self.sandbox_process.start()
        self.send_start()
        self.poll_until('Init Done')
        if self.sandbox_process == None:
            print('<CREATE FAILED>')
            exit(1)

    def terminate_sandbox(self):
        if self.sandbox_process == None:
            return

        print('<TERMINATE Id:%s>' % (self.sandbox_id), file=sys.stderr)
        self.sandbox_process.terminate()
        self.sandbox_process.join()
        self.sandbox_process = None
        self.control_socket = None
        self.console_socket = None
        self.state = 'Terminated'

    def invoke(self, event, context):
        self.start_sandbox()
        self.send_invoke(event, context)
        self.poll_until('Invoke Done')
        return self.result
        
    def start_bootstrap(self, control, console):
        bootstrap_path = os.path.join(os.path.dirname(__file__), 'awslambda', 'bootstrap.py')
        bootstrap_env = self.setup_environment(str(control.fileno()), str(console.fileno()))
        os.chdir(self.path)
        os.setsid()
        os.execle(sys.executable, sys.executable, '-B', bootstrap_path, bootstrap_env)

    def setup_environment(self, control_fd, console_fd):
        environ = {}
        runtime_dir = os.path.dirname(__file__)
        ex_path = ['/usr/local/bin', '/usr/bin', '/bin']
        py_path = [runtime_dir]
        ld_path = ['/lib64', '/usr/lib64', 
                   runtime_dir, os.path.join(runtime_dir, 'lib'), 
                   self.path, os.path.join(self.path, 'lib')]

        # Include unpackaged virtualenv if present to make development easier
        if 'VIRTUAL_ENV' in os.environ:
            venv = os.environ['VIRTUAL_ENV']
            ex_path.insert(0, os.path.join(venv, 'bin'))
            py_path.insert(0, venv)
            ld_path.insert(0, os.path.join(venv, 'lib'))

        # These are used by the native runtime support lib and explicitly clearned out by the bootstrap code
        environ["_LAMBDA_SHARED_MEM_FD"] = '-1'
        environ["_LAMBDA_LOG_FD"] = '-1'
        environ["_LAMBDA_CONSOLE_SOCKET"] = console_fd
        environ['_LAMBDA_CONTROL_SOCKET'] = control_fd
        environ["_LAMBDA_RUNTIME_LOAD_TIME"] = '%d' % (time.time() * 1000000000)

        # AWS environment has /etc/localtime -> /usr/share/zoneinfo/UTC
        # but we fake it by just setting TZ
        environ['TZ'] = 'UTC'

        # Base execution environment
        environ['LD_LIBRARY_PATH'] = os.pathsep.join(ld_path)
        environ['PYTHONPATH'] = os.pathsep.join(py_path)
        environ['PATH'] = os.pathsep.join(ex_path)

        # Remaining vars need to be set for a Lambda-like environment
        environ['LAMBDA_RUNTIME_DIR'] = runtime_dir
        environ['LAMBDA_TASK_ROOT'] = self.path
        environ['AWS_DEFAULT_REGION'] = self.session.region_name
        environ['AWS_REGION'] = self.session.region_name

        environ['AWS_LAMBDA_FUNCTION_NAME'] = self.name
        environ['AWS_LAMBDA_LOG_GROUP_NAME'] = '/aws/lambda/%s' % (self.name)
        environ['AWS_LAMBDA_LOG_STREAM_NAME'] = '%s/[%s]%s' % (time.strftime('%Y/%m/%d'), self.version, self.sandbox_id)
        environ['AWS_LAMBDA_FUNCTION_VERSION'] = self.version
        environ['AWS_LAMBDA_FUNCTION_MEMORY_SIZE'] = self.memory

        # Override defaults with user variables
        for (key, val) in self.variables.items():
            environ[key] = val

        return environ

    def poll_until(self, state):
        while self.state != state:
            if self.control_socket.poll(0.1):
                message = self.control_socket.recv()
                name = message.get('name')
                args = message.get('args', [])

                if   name == 'running':
                    self.sandbox_running(*args)
                elif name == 'fault':
                    self.sandbox_fault(*args)
                elif name == 'done':
                    self.sandbox_done(*args)
                elif name == 'console':
                    self.receive_console_message(*args)
                elif name == 'log':
                    self.receive_log_bytes(*args)
                elif name == 'remaining':
                    self.remaining_time(*args)
                else:
                    raise RuntimeError('Received unknown message from pipe') 
            elif self.sandbox_process.exitcode != None:
                self.terminate_sandbox()
                self.sandbox_done(self.invoke_id, 'unhandled', '{"errorMessage": "Process exited before completing request"}')
                return                


    def send_start(self):
        boto_creds = self.session.get_credentials().get_frozen_credentials()
        mode = "event"
        suppress_init = 0 if self.state == 'Uninitialized' else 1
        credentials = {'key': boto_creds.access_key, 'secret': boto_creds.secret_key, 'session': boto_creds.token}

        print("<RUN Mode:%s Handler:%s Suppress_init:%s>" % (mode, self.handler, suppress_init), file=sys.stderr)
        self.control_socket.send({'name': 'start',
                                  'args': (self.invoke_id, mode, self.handler, suppress_init, credentials)
                                  })
        self.state = 'Starting'

    def sandbox_running(self, invokeid):
        assert self.invoke_id == invokeid
        self.state = 'Running'
        print("<RUNNING>", file=sys.stderr)

    def send_invoke(self, event, context):
        boto_creds = self.session.get_credentials().get_frozen_credentials()
        data_sock = None
        credentials = {'key': boto_creds.access_key, 'secret': boto_creds.secret_key, 'session': boto_creds.token}
        arn = 'arn:aws:lambda:%s:%s:function:%s' % (self.session.region_name, self.account_id, self.name)

        self.receive_console_message("START RequestId: %s Version: %s\n" % (self.invoke_id, self.version))
        self.control_socket.send({'name': 'invoke',
                                  'args': (self.invoke_id, data_sock, credentials, event, self.make_context(context), arn, None, None, None)
                                  })
        self.state = 'Invoking'

    def sandbox_fault(self, invokeid, msg, except_value, trace):
        assert self.invoke_id == invokeid
        print("%s: %s\n%s" % (msg, except_value, trace), file=sys.stderr)

    def sandbox_done(self, invokeid, errortype=None, result=None):
        assert self.invoke_id == invokeid
        duration = (datetime.now() - self.start_time).total_seconds() * 1000

        if result:
            self.result = json.loads(result)

        if self.state == 'Running':
            self.state = 'Init Done'
        elif self.state in ['Invoking', 'Terminated']:
            billed = math.ceil(duration / 100.0) * 100
            print("END: RequestId: %s" % (invokeid), file=sys.stderr)
            print("REPORT: RequestId: %s Duration: %0.2f ms Billed Duration: %d ms Memory Size: %s MB Max Memory Used: %s MB" 
                  % (invokeid, duration, billed, self.memory, 'N/A'), file=sys.stderr)
            self.state  = 'Invoke Done'
            self.invoke_id = str(uuid.uuid4())
    
    def receive_console_message(self, msg):
        sys.stderr.write(msg)

    def receive_log_bytes(self, msg, fileno):
        sys.stderr.write(msg)
        
    def remaining_time(self):
        remaining_seconds = self.timeout
        if self.start_time:
            remaining_seconds -= (datetime.now() - self.start_time).total_seconds()
        self.control_socket.send({'name': 'remaining',
                                  'args': remaining_seconds * 1000.0
                                  })
