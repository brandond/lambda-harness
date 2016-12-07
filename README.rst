Python Lambda Test Harness
==========================

Sets up and executes Python code in a method highly analagous to the Lambda runtime environment.

Current notable gaps include:
* No support for runtime or memory limits
* No support for intra-execution cgroup freeze/thaw

Other than these caveats, it should look and feel roughly like a real Lambda execution, including all the correct environment variables, data structures, and log messages.

Check out the page on _GitHub: https://github.com/brandond/lambda-harness_ for complete documentation.

-------
Example
-------

::
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

-----
Usage
-----

Bootstrap once, then invoke::
  lambda bootstrap
  lambda invoke --path /path/to/lambda/
