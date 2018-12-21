# sumologic-securityhub-forwarder

This lambda function is used for importing findings from Sumo Logic to AWS Security Hub.


Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

![Sumo to Security Hub Collection Flow](https://s3.amazonaws.com/appdev-cloudformation-templates/sumologic-securityhub-forwarder.png)

## Setup

1. Enable Sumo Logic as a finding provider. Refer the [docs](https://www.google.com/url?q=https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-providers.html&sa=D&ust=1543440246819000&usg=AFQjCNEgjGnz7fQlpLFo2Rkqd5ZeQBDQ3w)

2. Deploying the SAM Application
    1. Go to https://serverlessrepo.aws.amazon.com/applications.
    2. Search for sumologic-securityhub-forwarder.
    3. Click on Deploy
    4. Copy the value of SecurityHubForwarderApiUrl from Output which is the API Gateway endpoint.

3. Create a [Webhook connection](https://help.sumologic.com/Manage/Connections-and-Integrations/Webhook-Connections/Webhook-Connection-for-AWS-Lambda).Use the value copied in step 1.4 as URL.
Note: SAM application already secures the endpoint with AWS_IAM authorization type
   It should have the following payload
```{
     "Types": "<type> Ex: Software and Configuration Checks/Industry and Regulatory Standards/PCI-DSS Controls",
     "Description": "{{SearchDescription}}",
     "SourceUrl": "{{SearchQueryUrl}}",
     "GeneratorID": "{{SearchName}}",
     "Severity": <number from 0 to 100>,
     "Rows": "{{AggregateResultsJson}}",
     "ComplianceStatus": "(Optional)<status> - PASSED/WARNING/FAILED/NOT_AVAILABLE"
  }
```
  Also make sure the IAM role or IAM user(whose credentials are used) has permissions to invoke the api in API Gateway. Refer the [docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html)

4. Create scheduled searches, as described in this [document](https://help.sumologic.com/Dashboards-and-Alerts/Alerts/02-Schedule-a-Search), and configure the following settings:
    * Alert condition is set to “Greater than >” and Number of Results is set to 0.
    * Alert Type is set to “Webhook”.
    * Connection is set to the name configured in step 2 (of the link document instructions).
    * Toggle the  customize payload button and fill the fields in the following dialog. The following table explains each field.

    | Field            | Description                             |
    | -----------------|-----------------------------------------|
    |Types             | Type of Finding in the format namespace/category/classifier.This field should match one of the finding types, as defined in Finding Type Taxonomy in AWS docs.
    | Description      | Details specific to the instance of the finding.This should be non empty.
    | SourceURL        | Search Query URL pointing to the exact query that generated the finding.
    | GeneratorID      | Scheduled Search Name that generated this finding.
    | Severity         | Impact of a finding has on a customer (data loss, malware activity, configuration weakness etc), displayed as an integer ranging from 0 to 100.
    | ComplianceStatus |  Results of a compliance check. This is an optional field and its value should be one of the following: PASSED/WARNING/FAILED/NOT_AVAILABLE.


Also the rows in AggregateResultsJson should contain following mandatory fields
"finding_time"(timestamp), "resource_type", "resource_id", "title"

“aws_account_id” is optional field in search results. Lambda function will pick up it’s value in following order
search results(each row) > aws_account_id environment variable > defaults to the account in which lambda is running


## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

