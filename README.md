Sumo Logic AWS Lambda Functions [![Build Status](https://travis-ci.org/SumoLogic/sumologic-aws-lambda.svg?branch=master)](https://travis-ci.org/SumoLogic/sumologic-aws-lambda)
==============================

| TLS Deprecation Notice |
| --- |
| In keeping with industry standard security best practices, as of May 31, 2018, the Sumo Logic service will only support TLS version 1.2 going forward. Verify that all connections to Sumo Logic endpoints are made from software that supports TLS 1.2. |

## What does AWS Lambda do? ##
AWS Lambda is a compute service that allows users to run code, in response to events, without having to provision and manage servers. A Lambda Function can be triggered automatically from other Amazon services, or from a web or mobile application.  For more information, please visit the [AWS Lambda site](https://aws.amazon.com/lambda/).

## What do Sumo Logic Lambda Functions do? ##
Sumo Logic Lambda Functions are designed to collect and process data from a variety of sources and pass it onto the Sumo Logic platform. Here, the data can be stored, aggregated, searched, and visualized for a variety of insightful use cases.

## What are the different Sumo Logic Lambda Functions available? ##
We put the Lambda functions to read from a particular AWS service (e.g CloudWatch Logs and S3) under each specific folder. Each folder may then have its own instructions to setup the functions. For example, for reading CloudWatch Logs, please refer to [Sumo Logic’s Lambda Function for Amazon CloudWatch Logs](https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/dlq_processor).


Supported Runtimes
======================

* All the nodejs functions are tested with nodejs runtime 4.3 and 8.10.

* All the python functions are tested with python version 2.7.

Testing with TravisCI
======================

* All the test are currently in python and travis.yml is configured to run any file with prefix "test_" present in lambda function's folder.

* All the dependencies(defined in package.json) of lambda function are installed first and then build is created.

* For adding test for new function you need to specify FUNCTION_DIR(lambda function's folder) and node_js(node js version) under jobs field in travis.yml. This is done because currently testing same function in parallel with different node versions throws function resource exists error (name collision) and therefore are run sequentially.
