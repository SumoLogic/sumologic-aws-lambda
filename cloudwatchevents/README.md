# Sumo Logic Function for AWS CloudWatch Events

AWS Lambda function to collect CloudWatch events and post them to [SumoLogic](http://www.sumologic.com) via a [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source)
AWS Cloudwatch Events invokes the function asynchronously in response to any changes in AWS resources. The event payload received is then sent to a SumoLogic HTTP source endpoint.

# Usage

First create an [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source) within SumoLogic. You will need the endpoint URL for the lambda function later.

## Create Lambda Function

1. Within the AWS Lambda console select create new Lambda function
2. Select `Blank Function` on the select blueprint page
3. Leave triggers empty for now, click next
4. Configure Lambda
   * Select Node.js 10.x as runtime
   * Copy code from cloudwatchevents.js into the Lambda function code.
   * Add Environment variables (See below)
5. Scroll down to the `Lambda function handle and role` section, make sure you set the right values that match the function. For role, you can just use the basic execution role. Click next.
6. Finally click on "Create function" to create the function.
7. (Optional) Test this new function with sample AWS CloudWatch Events template provided by AWS


# Lambda Environment Variables

The following AWS Lambda environment variables are supported

* `SUMO_ENDPOINT` (REQUIRED) - SumoLogic HTTP Collector [endpoint URL](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source).
* `SOURCE_CATEGORY_OVERRIDE` (OPTIONAL) - Override _sourceCategory metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_HOST_OVERRIDE` (OPTIONAL) - Override _sourceHost metadata field within SumoLogic. If `none` will not be overridden
* `SOURCE_NAME_OVERRIDE` (OPTIONAL) - Override _sourceName metadata field within SumoLogic. If `none` will not be overridden

# Excluding Outer Event Fields
By default, a CloudWatch Event has a format similar to this:

```
{
"version":"0",
"id":"0123456d-7e46-ecb4-f5a2-e59cec50b100",
"detail-type":"AWS API Call via CloudTrail",
"source":"aws.logs",
"account":"012345678908",
"time":"2017-11-06T23:36:59Z",
"region":"us-east-1",
"resources":[ ],
"detail":▶{ … }
}
```

This event will be sent as-is to Sumo Logic. If you just want to send the ```detail``` key instead, set the ```removeOuterFields``` variable to true.

# Running Tests
pip install aws-sam-cli
Configure credentials in "~/.aws/credentials"
export SUMO_ENDPOINT = HTTP_SOURCE_URL
Create a S3 bucket in AWS with following policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "serverlessrepo.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::bucket_name/*"
        }
    ]
}
```
export SAM_S3_BUCKET = bucket_name (configure in previous step)
npm test



