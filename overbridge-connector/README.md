# overbridge-connector

This lambda function is used for importing findings from Sumo Logic to AWS Overbridge.



## Setup
1. Create a (Webhook connection)[https://help.sumologic.com/Manage/Connections-and-Integrations/Webhook-Connections/Set-Up-Webhook-Connections].
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
2. Create a (Scheduled Search)[https://help.sumologic.com/Dashboards-and-Alerts/Alerts/02-Schedule-a-Search].
Also the rows in AggregateResultsJson should contain following mandatory fields
"finding_time", "resource_type", "resource_id", "severity_product", "severity_normalized"
3. Create a Lambda function by uploading the (overbridgePackage.zip)[] package
4. Create a following inline policy in role of lambda function
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "overbridgebeta:ImportFindings",
                "overbridgebeta:GetFindings"
            ],
            "Resource": "*"
        }
    ]
}
```
5. Set up (Lambda Proxy Integration in API Gateway)[https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format]
