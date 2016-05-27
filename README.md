Sumo Logic AWS Lambda Functions
==============================

## What does AWS Lambda do? ##
AWS Lambda is a compute service that allows users to run code, in response to events, without having to provision and manage servers. A Lambda Function can be triggered automatically from other Amazon services, or from a web or mobile application.  For more information, please visit the [AWS Lambda site](https://aws.amazon.com/lambda/).

## What do Sumo Logic Lambda Functions do? ##
Sumo Logic Lambda Functions are designed to collect and process data from a variety of sources and pass it onto the Sumo Logic platform. Here, the data can be stored, aggregated, searched, and visualized for a variety of insightful use cases.

## What are the different Sumo Logic Lambda Functions available? ##
We put the Lambda functions to read from a particular AWS service (e.g CloudWatch Logs and S3) under each specific folder. Each folder may then have its own instructions to setup the functions. For example, for reading CloudWatch Logs, please refer to [Sumo Logic’s Lambda Function for Amazon CloudWatch Logs](https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/cloudwatchlogs). 

