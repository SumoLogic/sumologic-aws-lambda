# Sumo Logic Functions for AWS CloudWatch Logs

AWS Lambda function to collector logs from CloudWatch Logs and post them to [SumoLogic](http://www.sumologic.com) via a [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source)

## Warning: This Lambda Function is no longer recommended solution
We recommend using [SumoLogic Lambda Function for AWS CloudWatch Logs With Dead Letter Queue Support](https://help.sumologic.com/Send-Data/Collect-from-Other-Data-Sources/Amazon-CloudWatch-Logs) as it is configured with Dead Letter Queue which takes care of messages that can't be processed (consumed) successfully.


# Usage

First create an [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source) within SumoLogic. You will need the endpoint URL for the lambda function later.

## Create Lambda Function

1. Within the AWS Lambda console select create new Lambda function
2. Select `Blank Function` on the select blueprint page
3. Leave triggers empty for now, click next
4. Configure Lambda
   * Select Node.js 10.x as runtime
   * Copy code from cloudwatchlogs_lambda.js into the Lambda function code.
   * Add Environment variables (See below)
5. Scroll down to the `Lambda function handle and role` section, make sure you set the right values that match the function. For role, you can just use the basic execution role. Click next.
6. Finally click on "Create function" to create the function.
7. (Optional) Test this new function with sample AWS CloudWatch Logs template provided by AWS

## Create Stream from CloudWatch Logs

1. Within the AWS CloudWatch Logs console, check the Log Group you want to send data to Sumologic.
2. From Actions button, select "Stream to AWS Lambda".
3. Select Lambda function created above.
4. Select `json` as the log format and define any filters.
5. Click start streaming.


# Lambda Environment Variables

The following AWS Lambda environment variables are supported

* `SUMO_ENDPOINT` (REQUIRED) - SumoLogic HTTP Collector [endpoint URL](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source).
* `ENCODING` (OPTIONAL) - Encoding to use when decoding CloudWatch log events. Default is 'utf-8'.
* `SOURCE_CATEGORY_OVERRIDE` (OPTIONAL) - Override _sourceCategory metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_HOST_OVERRIDE` (OPTIONAL) - Override _sourceHost metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_NAME_OVERRIDE` (OPTIONAL) - Override _sourceName metadata field within SumoLogic. If `none` will not be overridden
* `LOG_STREAM_PREFIX` (OPTIONAL) - Comma separated list of logStream name prefixes to filter by logStream, especially for AWS Batch logs

# Dynamic Metadata Fields

The lambda supports dynamically overriding the _sourceName, _sourceHost and _sourceCategory per log message by setting `_sumo_metadata` within a json log.

This can be useful when writing to CloudWatch Logs via a lambda function.

For example:

```
exports.handler = (event, context, callback) => {

    var serverIp = '123.123.123.123'

    console.log(JSON.stringify({
        'message': 'something happened..',
        '_sumo_metadata': {
            'category': 'prod/appa/console',
            'source': 'other_source',
            'host': serverIp
        }

    }));
    console.log('some other log message with default sourceCategory');
};

```
