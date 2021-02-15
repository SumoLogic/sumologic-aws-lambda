# sumologic-kinesis-firehose-collection

This Server Less application is used to setup aws resources required to send cloudwatch logs and metrics to Sumo Logic using Amazon Kinesis Firehose.

Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

### Deploying the SAM Application

    1. Open a browser window and enter the following URL: https://serverlessrepo.aws.amazon.com/applications
    2. Select Show apps that create custom IAM roles or resource policies check box.
    3. In the Serverless Application Repository, search for sumologic-kinesis-firehose-collection.
    4. Click the sumologic-kinesis-firehose-collection link, and then click Deploy.
    5. In the Configure application parameters panel,
        Section1aCollectLogs: "Collect AWS CloudWatch Logs using Kinesis Firehose."
                               1. Yes - Install all AWS resources to collect AWS Cloudwatch logs using kinesis Firehose.
                               2. No - Skips the collection of AWS Cloudwatch logs.
        Section1bSumoLogicKinesisLogsURL: "Required when collecting AWS Cloudwatch Logs using Kinesis firehose. 
                                           Provide HTTP Source Address from AWS Kinesis Firehose for Logs source created on your Sumo Logic account."
        
        Section2aCreateS3Bucket: "Create AWS S3 Bucket"
                               1. Yes - Create a new AWS S3 Bucket to store failed data.
                               2. No - Use an existing AWS S3 Bucket to store failed data.
        Section2bFailedDataS3Bucket: "Provide a unique name of AWS S3 bucket where you would like to store Failed logs. 
                                      For Logs, prefix is SumoLogic-Kinesis-Failed-Logs. For Metrics, prefix is SumoLogic-Kinesis-Failed-Metrics"         
                       
    6. Click Deploy.

## License

Apache License 2.0 (Apache-2.0)

## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

