Python Lambda Test Harness
==========================

Sets up and executes Python code in a method highly analagous to the Lambda runtime environment.

Current notable gaps include:
* No support for runtime or memory limits
* No support for intra-execution cgroup freeze/thaw

Other than these caveats, it should look and feel roughly like a real Lambda execution, including all the correct environment variables, data structures, and log messages.


Example
=======

```
[user@host ~]$ invoke-lambda --path ~/lambdas/Exec_Command_Example/ --payload '{"command": "echo Hello, World"}'
<CREATE Id:3d57aea1ba1e421a9f071ba741a278cb>
<RUN Mode:event Handler:function.lambda_handler Suppress_init:0>
<RUNNING>
[INFO]  2016-12-07T00:38:29.752Z                Function module init() called
START RequestId: 3773e161-e0af-437e-aa95-cd6dea0e457e Version: $LATEST
[INFO]  2016-12-07T00:38:29.752Z        3773e161-e0af-437e-aa95-cd6dea0e457e    Running command: echo Hello, World
END: RequestId: 3773e161-e0af-437e-aa95-cd6dea0e457e
Hello, World

<TERMINATE Id:3d57aea1ba1e421a9f071ba741a278cb>
```

Bootstrap
=========

`lambda bootstrap`

In order to accurately simulate the AWS Lambda environment, several Python modules must be extracted from the Lambda filesystem and made available to the Python module. This is done by:
* Creating a temporary Role and Lambda
* Invoking the Lambda to extract the files
* removing the Role and Lambda. 

The Lambda does need ANY rights; indeed the temporary role has no policies attached to it. Your AWS user must have access to create and delete IAM Roles and Lambda Functions.

Bootstrap Usage
---------------

```
Usage: lambda bootstrap [OPTIONS]

Options:
  --profile TEXT            Use a specific profile from your credential file.
  --region TEXT             The region to use. Overrides config/env settings.
  --cleanup / --no-cleanup  Do not remove bootstrap role and lambda after code
                            extraction
 --help                     Show this message and exit.
```

Invoke
======

`lambda invoke --path <path/to/lambda/directory>`

You should provide a path to a directory containing both the Lambda module, and a [lambda-uploader](https://github.com/rackerlabs/lambda-uploader) compatible `lambda.json` file describing the execution environment

The payload and client-context parameters may contain either raw JSON, or a URI (`file://`, `http://`, etc) of a file that will be processed as [newline delimited JSON](http://specs.okfnlabs.org/ndjson/index.html).

Invoke Usage
------------

```
Usage: lambda invoke [OPTIONS]

Options:
  --path PATH            The path to your Python Lambda function and
                         configuration  [required]
  --payload TEXT         JSON that you want to provide to your Lambda function
                         as input.
  --client-context TEXT  Client-specific information as base64-encoded JSON.
  --qualifier TEXT       Lambda function version or alias name.
  --profile TEXT         Use a specific profile from your credential file.
  --region TEXT          The region to use. Overrides config/env settings.
  --help                 Show this message and exit.
```

Notes
=====

Credentials for any AWS API calls made by your function are provided by your AWS CLI Profile. Ensure that the profile you have selected (with the `--profile` option) has the appropriate rights.

