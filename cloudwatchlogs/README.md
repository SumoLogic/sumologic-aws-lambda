Sumo Logic Functions for AWS CloudWatch Logs 
===========================================

AWS Lambda function to collector logs from CloudWatch Logs and post them to [SumoLogic](http://www.sumologic.com) via a [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source)


Usage
-----
1. First create an [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source) within SumoLogic. You will need the endpoint URL for the lambda function later.
2. Within the AWS CloudWatch Logs console, check the Log Group you want to send data to Sumologic. From Actions button, select "Start Streaming to Lambda Service", then "Create a Lambda function"
3. Select *Blank Function* on the select blueprint page
4. Configure Lambda
   * Select Node.js 4.3 as runtime
   * Copy code from cloudwatchlogs_lambda.js into the Lambda function code.
   * Add Environment variables (See below for options)
5. Scroll down to the *Lambda function handle and role* section, make sure you set the right values that match the function. For role, you can just use the basic execution role. Click next.
6. Finally click on "Create function" to create the function. 
7. (Optional) Test this new function with sample AWS CloudWatch Logs template provided by AWS
NOTE: If you are interested in **Lambda logs** (via CloudWatchLogs) specifically, please visit this [KB article](http://help.sumologic.com/Apps/AWS_Lambda/Collect_Logs_for_AWS_Lambda?t=1461360129021)  


Lambda Environment Variables
----------------------------
The following Environment variables are supported

* `SUMO_ENDPOINT` (REQUIRED) - SumoLogic HTTP Collector [endpoint URL](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source).
* `SOURCE_CATEGORY_OVERRIDE` (OPTIONAL) - Override _sourceCategory metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_HOST_OVERRIDE` (OPTIONAL) - Override _sourceHost metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_NAME_OVERRIDE` (OPTIONAL) - Override _sourceName metadata field within SumoLogic. If `none` will not be overridden

Dynamic Metadata Fields
-----------------------
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