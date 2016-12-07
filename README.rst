Python Lambda Test Harness
==========================

Sets up and executes Python code in a method highly analogous to the Lambda runtime environment.

Current notable gaps include:

* No support for runtime or memory limits
* No support for intra-execution cgroup freeze/thaw

Other than these caveats, it should look and feel roughly like a real Lambda execution, including all the correct environment variables, data structures, and log messages.

Check out the page on `GitHub <https://github.com/brandond/lambda-harness>`_ for complete documentation.

-------
Example
-------

::

  [user@host ~]$ lambda invoke --path ~/lambdas/Exec_Command_Example/ --payload '{"command": "echo Hello, World"}'
  <CREATE Id:4771091906264488b7ad71f930e2aea0>
  <RUN Mode:event Handler:function.lambda_handler Suppress_init:0>
  <RUNNING>
  [INFO]  2016-12-07T08:54:13.632Z                Function module init() called
  START RequestId: b64c27dc-0fe6-4ba7-9123-24ea0cc3072f Version: $LATEST
  [INFO]  2016-12-07T08:54:13.633Z        b64c27dc-0fe6-4ba7-9123-24ea0cc3072f    Running command: echo Hello, World
  END: RequestId: b64c27dc-0fe6-4ba7-9123-24ea0cc3072f
  REPORT: RequestId: b64c27dc-0fe6-4ba7-9123-24ea0cc3072f Duration: 92.31 ms Billed Duration: 100 ms Memory Size: 128 MB Max Memory Used: N/A MB
  Hello, World

  <TERMINATE Id:4771091906264488b7ad71f930e2aea0>

-----
Usage
-----

Bootstrap once, then invoke::

  lambda bootstrap
  lambda invoke --path /path/to/lambda/

