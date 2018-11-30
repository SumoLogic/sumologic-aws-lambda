Sumo Logic AWS Lambda Functions [![Build Status](https://travis-ci.org/SumoLogic/sumologic-aws-lambda.svg?branch=master)](https://travis-ci.org/SumoLogic/sumologic-aws-lambda)
==============================

## What does AWS Lambda do? ##
AWS Lambda is a compute service that allows users to run code, in response to events, without having to provision and manage servers. A Lambda Function can be triggered automatically from other Amazon services, or from a web or mobile application.  For more information, please visit the [AWS Lambda site](https://aws.amazon.com/lambda/).

## What do Sumo Logic Lambda Functions do? ##
Sumo Logic Lambda Functions are designed to collect and process data from a variety of sources and pass it onto the Sumo Logic platform. Here, the data can be stored, aggregated, searched, and visualized for a variety of insightful use cases.

## What are the different Sumo Logic Lambda Functions available? ##
We put the Lambda functions to read from a particular AWS service (e.g CloudWatch Logs and S3) under each specific folder. Each folder may then have its own instructions to setup the functions.

## Collection Solutions
| FunctionName | Description | Collection Use Cases | Setup Documentation
| -------------| ----------- | -------------- | ------------------- |
|[SumoLogic Lambda Function for AWS CloudWatch Logs With Dead Letter Queue Support](cloudwatchlogs-with-dlq)| This project comes with Cloudformation template and two lambda functions which sends CloudWatch logs to Sumo Logic HTTP source endpoint.The first function(invoked by CloudWatch) is configured with DLQ and the second function(invoked periodically by CloudWatch Events) reads from DLQ.| [AWS Lambda ULM App](https://help.sumologic.com/Send-Data/Applications-and-Other-Data-Sources/AWS_Lambda_ULM/Collect_Logs_and_Metrics_for_AWS_Lambda_ULM) | [Docs](https://help.sumologic.com/Send-Data/Collect-from-Other-Data-Sources/Amazon-CloudWatch-Logs)|
|[SumoLogic Function for AWS CloudWatch Events](cloudwatchevents) | This function is invoked by AWS CloudWatch events in response to state change in your AWS resources which matches a event target definition. The event payload received is then forwarded to Sumo Logic HTTP source endpoint. | [AWS GuardDuty App](https://help.sumologic.com/Send-Data/Applications-and-Other-Data-Sources/Amazon-GuardDuty/Collect-Amazon-GuardDuty-Log-Files) | [Docs](cloudwatchevents/README.md) |
|[SumoLogic Function for Amazon Inspector](inspector) | This function subscribes to a SNS topic where Amazon Inspector publishes its findings.It receives the message payload as an input parameter, transforms it and sends it to Sumo Logic HTTP source endpoint| [Amazon Inspector](https://help.sumologic.com/Send-Data/Applications-and-Other-Data-Sources/Amazon-Inspector-App/) | [Docs](https://help.sumologic.com/Send-Data/Applications-and-Other-Data-Sources/Amazon-Inspector-App/01-Collect-Data-for-Amazon-Inspector) |
|[Kinesis to Sumo Logic](kinesis)| This function is invoked by AWS Lambda after it detects new records in Kinesis stream. The received collection of events are decompressed, transformed and send to Sumo Logic HTTP source endpoint |  | [Docs](kinesis/README.md#lambda-configuration) |
|[SumoLogic Lambda Function for AWS CloudWatch Logs](cloudwatchlogs)| This function subscribes to CloudWatch Log Group and is invoked by AWS CloudWatch with log messages as payload. The records received are decompressed, transformed and  forwarded to Sumo Logic HTTP source endpoint in chunks.While the function is more simple then the DLQ-based solution above, it doesn't handle failures and retries properly, thus not recommended. | Not Recommended | [Docs](https://help.sumologic.com/Send-Data/Collect-from-Other-Data-Sources/Create-an-Amazon-Lambda-Function) |
| [S3](s3) AND <br> [Cloudtrail S3 to Sumo Logic](cloudtrail_s3)| This function receives S3 notifications on new files uploaded to the source S3 bucket, then reads these files, unzips them, and breakdown the records before finally sending to HTTP hosted collector endpoint. | DEPRECATED | [Docs](s3/README.md#lambda-setup) <br> [Docs](cloudtrail_s3#lambda-setup)|

## Helper Functions

| FunctionName | Description | Setup Documentation
| -------------| ----------- | ------------------- |
|[Kinesis Firehose Processor](kinesisfirehose-processor)|This function is used for transforming streaming data from kinesis firehose before it sents to destination. | [Docs](kinesisfirehose-processor#setting-up-the-lambda-function) |
|[LogGroup Lambda Connector](loggroup-lambda-connector) | This function is used to automatically subscribe newly created and existing Cloudwatch LogGroups to a Lambda function. | [Docs](https://help.sumologic.com/Send-Data/Collect-from-Other-Data-Sources/Auto-Subscribe_AWS_Log_Groups_to_a_Lambda_Function) |


Supported Runtimes
======================

* All the nodejs functions are tested with nodejs runtime 4.3 and 8.10.

* All the python functions are tested with python version 2.7.

Testing with TravisCI
======================

* All the test are currently in python and travis.yml is configured to run any file with prefix "test_" present in lambda function's folder.

* All the dependencies(defined in package.json) of lambda function are installed first and then build is created.

* For adding test for new function you need to specify FUNCTION_DIR(lambda function's folder) and node_js(node js version) under jobs field in travis.yml. This is done because currently testing same function in parallel with different node versions throws function resource exists error (name collision) and therefore are run sequentially.


### TLS 1.2 Requirement

Sumo Logic only accepts connections from clients using TLS version 1.2 or greater. To utilize the content of this repo, ensure that it's running in an execution environment that is configured to use TLS 1.2 or greater.
