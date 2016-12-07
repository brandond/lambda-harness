from __future__ import print_function
import botocore
import inspect
import tarfile
import zipfile
import base64
import boto3
import json
import time
import bz2
import io
import os

class Extractor(object):

    def __init__(self, profile, region, cleanup):
        session = boto3.session.Session(profile_name=profile, region_name=region)
        self.cleanup = cleanup
        self.iam = session.client('iam')
        self.lam = session.client('lambda')

    def extract(self):
        role_arn = None
        func_arn = None
        try:
            role_arn = self.create_lambda_role()
            func_arn = self.create_lambda_function(role_arn)
            func_res = self.invoke_lambda(func_arn)
            self.extract_payload(func_res)
        except Exception as e:
            print('Failed to bootstrap: {0}'.format(e))
        finally:
            if self.cleanup:
                if func_arn:
                    self.delete_lambda_function(func_arn)
                if role_arn:
                    self.delete_lambda_role(role_arn)
            
        
    def create_lambda_role(self):
        print('Creating role: {0}'.format(self.ROLE_NAME))
        try:
            response = self.iam.create_role(RoleName=self.ROLE_NAME,
                                            AssumeRolePolicyDocument=inspect.cleandoc(self.ROLE_POLICY))
            print('Waiting 15 seconds for role creation to complete...')
            time.sleep(15)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print('Role already exists')
                response = self.iam.get_role(RoleName=self.ROLE_NAME)
            else:
                raise
        return response['Role']['Arn']

    def delete_lambda_role(self, role_arn):
        print('Deleting role: {0}'.format(role_arn))
        self.iam.delete_role(RoleName=self.ROLE_NAME)

    def create_lambda_function(self, role_arn):
        print('Creating function: {0}'.format(self.FUNC_NAME))
        try:
            response = self.lam.create_function(FunctionName=self.FUNC_NAME,
                                                Runtime='python2.7',
                                                Role=role_arn,
                                                Handler='function.handler',
                                                Code={'ZipFile': self.get_zip_bytes()},
                                                Description='Extracts awslambda runtime module from Lambda environment')
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                print('Function already exists; updating code')
                response = self.lam.update_function_code(FunctionName=self.FUNC_NAME, ZipFile=self.get_zip_bytes())
            else:
                raise
        return response['FunctionArn']

    def delete_lambda_function(self, func_arn):
        print('Deleting function: {0}'.format(func_arn))
        self.lam.delete_function(FunctionName=self.FUNC_NAME)

    def invoke_lambda(self, function_arn):
        print('Invoking function: {0}'.format(function_arn))
        response = self.lam.invoke(FunctionName=function_arn)
        return response

    def extract_payload(self, response):
        if response['StatusCode'] == 200 and not 'FunctionError' in response:
            print('Extracting awslambda from response')
            res_bytes = json.load(response['Payload'])
            tar_bytes = io.BytesIO()
            tar_bytes.write(base64.b64decode(res_bytes))
            tar_bytes.seek(0)
            with tarfile.open(fileobj=tar_bytes) as tar_file:
                tar_file.list(verbose=True)
                tar_file.extractall(path=os.path.join(os.path.dirname(__file__), 'awslambda'))
            print('Modules successfully extracted')
        else:
            raise RuntimeError('Invocation failed: {FunctionError}'.format(**response))

    def get_zip_bytes(self):
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, 'w') as zip_file:
            zipinfo = zipfile.ZipInfo(filename='function.py', date_time=time.gmtime())
            zipinfo.external_attr = 0o100664 << 16
            zip_file.writestr(zipinfo, inspect.cleandoc(self.FUNC_CODE), zipfile.ZIP_DEFLATED)
        return zip_bytes.getvalue()

    FUNC_NAME = 'Invoke-Lambda_Bootstrap_Lambda'
    ROLE_NAME = 'Invoke-Lambda_Bootstrap_Role'
    ROLE_POLICY = """
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    """
    FUNC_CODE = """
    import tarfile
    import base64
    import os
    import io

    # Begin Handler
    def handler(event,context):
        tar_bytes = io.BytesIO()
        with tarfile.open(mode='w:bz2', fileobj=tar_bytes) as tar_file:
            for py_file in ('bootstrap.py','wsgi.py'):
                py_path = os.path.join(os.environ['LAMBDA_RUNTIME_DIR'], 'awslambda', py_file)
                tar_file.add(py_path, arcname=py_file)
        return base64.b64encode(tar_bytes.getvalue())
    # End Handler
    """
