# sumologic-securityhub-processor

This solution consists of two lambda functions which are used to fetch findings from AWS Security Hub and ingest to Sumo Logic.



Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![Sumo to Security Hub Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-securityhub-processor.png)

## Setup


1. Configure a [Hosted Collector](https://help.sumologic.com/03Send-Data/Hosted-Collectors/Configure-a-Hosted-Collector) and  an [AWS S3 Source](https://help.sumologic.com/03Send-Data/Sources/02Sources-for-Hosted-Collectors/Amazon-Web-Services/AWS-S3-Source#AWS_Sources) to Sumo Logic, and in Advanced Options for Logs, under Timestamp Format, click Specify a format and enter the following:
Specify Format as yyyy-MM-dd'T'HH:mm:ss.SSS'Z'
Specify Timestamp locator as .*"UpdatedAt":"(.*)".*

2. Deploying the SAM Application
    1. Go to https://serverlessrepo.aws.amazon.com/applications.
    2. Search for sumologic-securityhub-processor, click the link in the panel, then click Deploy.
    3. In the Configure application parameters panel, paste the HTTP collector endpoint you configured previously.
    4. Click Deploy.


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

