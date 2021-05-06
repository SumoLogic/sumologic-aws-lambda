# sumologic-kinesis-cloudwatch-logs

This CloudFormation template is used to setup aws resources required to send cloudwatch logs to Sumo Logic using Amazon Kinesis Firehose.

Made with ❤️ by Sumo Logic.

### Deploying the SAM Application

    1. Sign on to the AWS Management console.
    2. Click this [URL](https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://sumologic-appdev-aws-sam-apps.s3.amazonaws.com/KinesisFirehoseCWLogs.template.yaml) to invoke the latest AWS CloudFormation template.
    3. In the parameters panel,
        Section1aSumoLogicKinesisLogsURL: "Provide HTTP Source Address from AWS Kinesis Firehose for Logs source created on your Sumo Logic account."
        
        Section2aCreateS3Bucket: "Create AWS S3 Bucket"
                               1. Yes - Create a new AWS S3 Bucket to store failed data.
                               2. No - Use an existing AWS S3 Bucket to store failed data.
        Section2bFailedDataS3Bucket: "Provide a unique name of AWS S3 bucket where you would like to store Failed data. 
                                      In case of existing AWS S3 bucket, provide the bucket from the current AWS Account. 
                                      For Logs, failed data will be stored in folder prefix as SumoLogic-Kinesis-Failed-Logs."         
                       
    6. Click Deploy.

## License

Apache License 2.0 (Apache-2.0)

## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

