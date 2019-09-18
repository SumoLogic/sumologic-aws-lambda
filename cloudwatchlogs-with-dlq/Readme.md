# SumoLogic Lambda Function for AWS CloudWatch Logs With Dead Letter Queue Support

This is used for collecting Amazon CloudWatch Logs.It provides two lambda functions

* SumoCWLogsLambda: It’s a lambda function responsible for sending data to Sumo logic HTTP endpoint.It is configured with dead letter queue(SumoCWDeadLetterQueue) which gets the messages which can’t be processed successfully. Also you can subscribe other logs to this function except its own log group.
* SumoCWProcessDLQLambda: It’s a lambda function responsible for reading messages from dead letter queue and retries sending messages.It gets triggered periodically by AWS CloudWatch Events using schedule rule(SumoCWProcessDLQScheduleRule).

It also configured with CloudWatch Alarm which triggers when number of messages in DeadLetterQueue exceeds threshold defined in cloudformation template.

### Creating Stack in AWS Cloudformation
you can create the stack by using [aws-cli](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-cli-creating-stack.html) or directly from aws console using webbrowser and uploading DLQLambdaCloudFormation.json. For more details checkout it's [documentation](https://help.sumologic.com/Send-Data/Collect-from-Other-Data-Sources/Amazon-CloudWatch-Logs)

### Configuring Lambda

The following AWS Lambda environment variables are supported in both the lambda functions.Please note that both the functions should have same values configured to avoid inconsistencies.

* SUMO_ENDPOINT (REQUIRED) - SumoLogic HTTP Collector endpoint URL.
* ENCODING (OPTIONAL) - Encoding to use when decoding CloudWatch log events. Default is 'utf-8'.
* SOURCE_CATEGORY_OVERRIDE (OPTIONAL) - Override _sourceCategory metadata field within SumoLogic.
* SOURCE_HOST_OVERRIDE (OPTIONAL) - Override _sourceHost metadata field within SumoLogic.
* SOURCE_NAME_OVERRIDE (OPTIONAL) - Override _sourceName metadata field within SumoLogic.
* INCLUDE_LOG_INFO (OPTIONAL) - Set it to true when loggroup/logstream values needs to be included in logs. Default is false
* LOG_FORMAT - Default is Others. One can choose VPC-JSON for VPC flow logs in json format and VPC-RAW for only RAW message line
* LOG_STREAM_PREFIX (OPTIONAL) - Comma separated list of logStream name prefixes to filter by logStream, especially for AWS Batch logs

### Configuring Lambda for VPC Flow Logs
The following AWS Lambda environment variables are supported in both the lambda functions for VPC flow logs.

* INCLUDE_SECURITY_GROUP_INFO (OPTIONAL) - Set it to true when security-group-ids/direction values needs to be included in logs.The lambda function fetches list of Elastic Network Interfaces using describeNetworkInterfaces api.
One needs to provide permission to lambda by adding the following inline policy in SumoCWProcessDLQLambda Role.
Refer this [doc](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html#add-remove-policies-console) for adding inline policy for a role. Choose [Creating Policies on the JSON Tab](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create.html#access_policies_create-json-editor) method and paste the below json after adding the arn of both the lambda functions.
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:DescribeNetworkInterfaces",
            "Resource": [
              <ARN of SumoCWProcessDLQLambda and SumoCWLogsLambda function created by the Cloudformation template>
            ]
        }
    ]
}
```
This will add two extra keys(security-group-ids and direction) in logs. This option works only when LOG_FORMAT is set to VPC-JSON.
* VPC_CIDR_PREFIX (OPTIONAL) - Comma separated list of ip prefixes for filtering out internal traffic. For Ex: lets say we have `vpcCIDRprefix= 10.8.0.0,10.9.0.0` then it will filter out logs whose destinationIP and sourceIP matches any of the two prefixes 10.8.0.0 and 10.9.0.0. This option works only when LOG_FORMAT is set to VPC-JSON or VPC-RAW.


SumoCWProcessDLQLambda supports one extra environment variable
* NUM_OF_WORKERS(REQUIRED): It’s default value is 4. It controls the number of instances of SumoCWProcessDLQLambda to spawn if there is no failure in first attempt.It helps in faster processing of pending messages in dead letter queue.

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
            'sourceName': 'other_source',
            'sourceHost': serverIp
        }

    }));
    console.log('some other log message with default sourceCategory');
};

```

### For Developers

Installing Dependencies
```
  npm install
```

Building zip file
```
  npm run build
```
Upload the generated cloudwatchlogs-with-dlq.zip in S3 bucket(don't forget to change bucket name and key in cloudformation template)

Running the test cases

```
  python test_cwl_lambda.py
```
Run the above command after building the zip file
