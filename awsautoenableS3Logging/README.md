# sumologic-s3-logging-auto-enable

This Server Less application is used to automatically enable logging to S3 buckets for [VPC, Subnets and Network Interfaces Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-s3.html), [S3 Buckets Audit Logging](https://docs.aws.amazon.com/AmazonS3/latest/dev/ServerLogs.html#server-access-logging-overview) and [Load Balancer Access logging](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#enable-access-logging). 

The application supports
 - **[S3 Audit Logging](https://docs.aws.amazon.com/AmazonS3/latest/dev/ServerLogs.html#server-access-logging-overview)** to S3 Buckets.
 - **[VPC flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-s3.html)** enable for VPC, Subnets and Network interfaces. FLow Logs for new VPC is enabled and AWS creates Flow Logs for any new Subnets or network interfaces attached to the VPC.
 - **[Load Balancer Access Logging](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#enable-access-logging)** enable for Load Balancer. 

Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

## AWS Resources

The Server Less Application can enable S3 logging for below AWS Resources.
 * **Existing AWS resources** - Lambda calls describe APIs to get existing resources and Enable S3 logging or VPC Flow logs.
 * **New AWS Resources** - Lambda is invoked on CLoudWatch Events after AWS Resource creation and Enable S3 logging or VPC Flow logs.  

### Deploying the SAM Application

    1. Open a browser window and enter the following URL: https://serverlessrepo.aws.amazon.com/applications
    2. Select Show apps that create custom IAM roles or resource policies check box.
    3. In the Serverless Application Repository, search for sumologic-s3-logging-auto-enable.
    4. Click the sumologic-s3-logging-auto-enable link, and then click Deploy.
    5. In the Configure application parameters panel,
        EnableLogging: "Select the AWS Resource from S3, VPC and ALB to enable logging for."
            1. S3 - To Enable S3 Audit Logging for new S3 buckets.
            2. VPC - To Enable VPC flow logs for new VPC, Subnets and Network Interfaces.
            3. ALB - To Enable S3 Logging for new Application Load Balancer.
        TaggingResourceOptions: "Select AWS Resource to tag from New and Existing."
            1. New - Automatically enables S3 logging for newly created AWS resources to send logs to S3 Buckets. This does not affect AWS resources already collecting logs.
            2. Existing - Automatically enables S3 logging for existing AWS resources to send logs to S3 Buckets.
            3. Both - Automatically enables S3 logging for new and existing AWS resources.
            4. None - Skips Automatic S3 Logging enable for AWS resources. 
        BucketName: "Provide the AWS S3 Bucket Name where logs should be sent"
        BucketPrefix: "Provide the prefix within the bucket to store logs."
        RemoveOnDeleteStack: "Disable the S3 logging for AWS Resources after the stack is deleted."
            1. True - To remove S3 logging or Vpc flow logs after stack is deleted.
            2. False - To keep the S3 logging after stack is deleted.
        ParentStackName: "DO NOT EDIT THE VALUE"
    6. Click Deploy.


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

