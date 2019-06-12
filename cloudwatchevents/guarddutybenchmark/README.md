# sumologic-guardduty-benchmark

This solution installs the Guardduty Benchmark App, creates collectors/sources in Sumo Logic platform and deploys the lambda function in your AWS account using configuration provided at the time of sam application deployment.


Made with ❤️ by Sumo Logic AppDev Team. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![GuardDuty Event Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-guardduty-evetns-processor.png)

## Setup
1. Generate Access key from sumologic console as per [docs](https://help.sumologic.com/Manage/Security/Access-Keys#Create_an_access_key).

2. Go to https://serverlessrepo.aws.amazon.com/applications.
3. Search for sumologic-guardduty-benchmark and click on deploy.
4. In the Configure application parameters panel, enter the following parameters
    * Access ID(Required): Sumo Logic Access ID generated from Step 1
    * Access Key(Required): Sumo Logic Access Key generated from Step 1
    * Deployment Name(Required): Deployment name (environment name in lower case as per [docs](https://help.sumologic.com/APIs/General-API-Information/Sumo-Logic-Endpoints-and-Firewall-Security))
    * Collector Name: Enter the name of the Hosted Collector which will be created in Sumo Logic.
    * Source Name: Enter the name of the HTTP Source which will be created within the collector.
    * Source Category Name: Enter the name of the Source Category which will be used for writing search queries.
5. Click on Deploy


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

