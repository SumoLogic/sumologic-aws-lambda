# Sumo Logic Security Hub Connector

This lambda function is used for importing findings from Sumo Logic to AWS Security Hub.


## Setup
1. Deploying the SAM Application
    1. Go to https://serverlessrepo.aws.amazon.com/applications.
    2. Search for sumologic-securityhub-connector.
    3. Click on Deploy
    4. Copy the value of SecurityHubConnectorApiUrl from Output which is the API Gateway endpoint.

2. Create a [Webhook connection](https://help.sumologic.com/Manage/Connections-and-Integrations/Webhook-Connections/Webhook-Connection-for-AWS-Lambda).Use the value copied in step 1.4 as URL.
Note: SAM application already secures the endpoint with AWS_IAM authorization type
   It should have the following payload
```{
  "Types": "<type> Ex: Software and Configuration Checks/Industry and Regulatory Standards/PCI-DSS Controls",
  "Description": "{{SearchDescription}}",
  "SourceUrl": "{{SearchQueryUrl}}",
  "GeneratorID": "{{SearchName}}",
  "Severity": <number from 0 to 100>,
  "Rows": "{{AggregateResultsJson}}"
  "ComplianceStatus"(Optional): "<status> - PASSED/WARNING/FAILED/NOT_AVAILABLE",
}
```
  Also make sure the IAM role or IAM user(whose credentials are used) has permissions to invoke the api in API Gateway. Refer the [docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html)

3. Create a [Scheduled Search](https://help.sumologic.com/Dashboards-and-Alerts/Alerts/02-Schedule-a-Search).
Also the rows in AggregateResultsJson should contain following mandatory fields
"finding_time"(timestamp), "resource_type", "resource_id", "title"

“aws_account_id” is optional field in search results. Lambda function will pick up it’s value in following order
search results(each row) > aws_account_id environment variable > defaults to the account in which lambda is running


## TroubleShooting
1) Test the API using mock data [fixtures.json](fixtures.json)
2) Monitor the scheduled search logs using following query in Sumo
```
_view=sumologic_audit "Scheduled search alert triggered" <webhook name>
```
3) Check CloudWatch logs for lambda function

