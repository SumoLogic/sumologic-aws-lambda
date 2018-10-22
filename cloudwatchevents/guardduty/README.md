# sumologic-guardduty-events-processor

This solution creates resources for processing and sending Amazon GuardDuty Events to Sumo logic.


Made with ❤️ by Sumo Logic AppDev Team. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![GuardDuty Event Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-guardduty-evetns-processor.png)

## Setup
1. First create an HTTP collector endpoint within SumoLogic. You will need the endpoint URL for the lambda function later.
2. Go to https://serverlessrepo.aws.amazon.com/applications.
3. Search for sumologic-guardduty-events-processor and click on deploy.
4. In Configure application parameters panel paste the HTTP collector endpoint previously configured.
5. Click on Deploy

## Lambda Environment Variables
The following AWS Lambda environment variables are supported

SUMO_ENDPOINT (REQUIRED) - SumoLogic HTTP Collector endpoint URL.
SOURCE_CATEGORY_OVERRIDE (OPTIONAL) - Override _sourceCategory metadata field within SumoLogic. If none will not be overridden
SOURCE_HOST_OVERRIDE (OPTIONAL) - Override _sourceHost metadata field within SumoLogic. If none will not be overridden
SOURCE_NAME_OVERRIDE (OPTIONAL) - Override _sourceName metadata field within SumoLogic. If none will not be overridden

## Excluding Outer Event Fields

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
This event will be sent as-is to Sumo Logic. If you just want to send the detail key instead, set the removeOuterFields variable to true.


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

