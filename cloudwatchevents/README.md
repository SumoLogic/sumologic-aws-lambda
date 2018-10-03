# Sumo Logic Function for AWS CloudWatch Events

AWS Lambda function to collect CloudWatch events and post them to [SumoLogic](http://www.sumologic.com) via a [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source)
AWS Cloudwatch Events invokes the function asynchronously in response to any changes in AWS resources. The event payload received is then sent to a SumoLogic HTTP source endpoint.

# Usage

* First create an [HTTP collector endpoint](http://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source) within SumoLogic. You will need the endpoint URL for the lambda function later.

* Go to https://serverlessrepo.aws.amazon.com/applications.
* Search for sumologic-guardduty-events-processor and click on deploy.
* In Configure application parameters panel paste the HTTP collector endpoint previously configured.
* Click on Deploy

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
