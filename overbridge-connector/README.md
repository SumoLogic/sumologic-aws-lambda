# Sumo Logic Overbridge Connector

This lambda function is used for importing findings from Sumo Logic to AWS Overbridge.


## Setup
1. Create a Lambda function by uploading the [securityHubPackage.zip](https://s3.amazonaws.com/appdevstore/securityHubPackage.zip) file.
2. Create a following inline policy in role of lambda function
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "securityhub:ImportFindings",
                "securityhub:GetFindings"
            ],
            "Resource": "*"
        }
    ]
}
```
3. Set up [Lambda Proxy Integration in API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format)
4. Create a [Webhook connection](https://help.sumologic.com/Manage/Connections-and-Integrations/Webhook-Connections/Set-Up-Webhook-Connections).
   It should have the following payload
```{
  "Types": "Security",
  "TimeRange": "{{TimeRange}}",
  "Description": "{{SearchDescription}}",
  "SourceUrl": "{{SearchQueryUrl}}",
  "FireTime": "{{FireTime}}",
  "GeneratorID": "{{SearchName}}",
  "Rows": "{{AggregateResultsJson}}"
}
```
  Also make sure the IAM role or IAM user(whose credentials are used) have permissions to invoke the api in API Gateway.

5. Create a [Scheduled Search](https://help.sumologic.com/Dashboards-and-Alerts/Alerts/02-Schedule-a-Search).
Also the rows in AggregateResultsJson should contain following mandatory fields
"finding_time", "resource_type", "resource_id", "severity_product", "severity_normalized"
finding_time should have following date format "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"

## TroubleShooting
1) Test the API using mock data [fixtures.json](fixtures.json)
2) Monitor the scheduled search logs using following query in Sumo
```
_view=sumologic_audit "Scheduled search alert triggered" <webhook name>
```
3) Check CloudWatch logs for lambda function

