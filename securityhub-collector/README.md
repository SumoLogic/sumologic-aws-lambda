# sumologic-securityhub-collector

This solution consists of a lambda function which which gets triggered by CloudWatch events with findings as payload which are then ingested to Sumo Logic via S3 source


Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![Sumo to Security Hub Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-securityhub-collector.png)

## Setup


1. Configure a [Hosted Collector](https://help.sumologic.com/03Send-Data/Hosted-Collectors/Configure-a-Hosted-Collector) and  an [AWS S3 Source](https://help.sumologic.com/03Send-Data/Sources/02Sources-for-Hosted-Collectors/Amazon-Web-Services/AWS-S3-Source#AWS_Sources) to Sumo Logic, and in Advanced Options for Logs, under Timestamp Format, click Specify a format and enter the following:
Specify Format as yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
Specify Timestamp locator as .*"UpdatedAt":"(.*)".*

2. Deploying the SAM Application
    1. Open a browser window and enter the following URL: https://serverlessrepo.aws.amazon.com/applications
    2. In the Serverless Application Repository, search for sumologic.
    3. Select Show apps that create custom IAM roles or resource policies check box.
    4. Click the sumologic-securityhub-collector,link, and then click Deploy.
    5. In the Configure application parameters panel, enter the name of the S3 bucket configured while creating AWS S3 source.
    Click Deploy.


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

