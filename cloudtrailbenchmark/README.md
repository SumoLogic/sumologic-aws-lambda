# sumologic-aws-cloudtrail-benchmark

This solution installs the AWS CloudTrail Benchmark App, creates collectors/sources in Sumo Logic platform and deploys the aws resources in your AWS account using configuration provided at the time of sam application deployment.


Made with ❤️ by Sumo Logic AppDev Team. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![aws-cloudtrail Event Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-aws-cloudtrail-benchmark.png)

## Setup
1. Generate Access key from sumologic console as per [docs](https://help.sumologic.com/Manage/Security/Access-Keys#Create_an_access_key).
2. Go to https://serverlessrepo.aws.amazon.com/applications.
3. Search for sumologic-aws-cloudtrail-benchmark and click on deploy.
4. In the Configure application parameters panel, enter the following parameters
    In Sumo Logic Deployment Configuration
    * `SumoAccessID`(Required): Sumo Logic Access ID generated from Step 1
    * `SumoAccessKey`(Required): Sumo Logic Access Key generated from Step 1
    * `DeploymentName`(Required): Deployment name (environment name in lower case as per [docs](https://help.sumologic.com/APIs/General-API-Information/Sumo-Logic-Endpoints-and-Firewall-Security))
    * `DeploymentType`: The deployment supports 3 modes.
        * `Only-App`: Select this mode if you already have cloud trail logs in Sumo. It installs only the app.
        * `App-SumoResources`: Select this mode if you already have a S3 bucket which is getting cloudtrail logs. It installs the collector, source and app.
        * `App-SumoResources-CloudTrail-S3Bucket`: Select this mode if you do not have Cloudtrail logs configured in your AWS Account. It creates a trail and S3 bucket along with sumo logic resources.
    * `RemoveSumoResourcesOnDeleteStack`: To delete collector, sources and app when stack is deleted, set this parameter to true. Default is false.
    * `SumoOrganizationID`(Required):  Organization from Account Overview tab in Sumo Logic console.
    * `CollectorName`: Enter the name of the Hosted Collector which will be created in Sumo Logic.
    * `SourceName`: Enter the name of the HTTP Source which will be created within the collector.
    * `SourceCategoryName`: Enter the name of the Source Category which will be used for writing search queries.
    * `CloudTrailTargetS3BucketName`: Enter the name of the S3 bucket containing cloudtrail logs
    * `S3PathExpression`: Enter the path to the cloudtrail logs folder in S3 bucket
5. Click on Deploy


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

