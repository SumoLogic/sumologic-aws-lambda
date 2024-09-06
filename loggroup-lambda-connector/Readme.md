# SumoLogic LogGroup Connector
This is used to automatically subscribe newly created and existing Cloudwatch LogGroups to a Lambda function.

> **Note:**
For existing CloudWatch LogGroups, a Lambda function can subscribe to up to 65,000 LogGroups.
If the number of LogGroups exceeds 65,000, you can request to disable Lambda recursive loop detection by [contact AWS Support](https://repost.aws/knowledge-center/aws-phone-support).


Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

### Deploying the SAM Application
    1. Open a browser window and enter the following URL: https://serverlessrepo.aws.amazon.com/applications
    2. In the Serverless Application Repository, search for sumologic.
    3. Select Show apps that create custom IAM roles or resource policies check box.
    4. Click the sumologic-loggroup-connector,link, and then click Deploy.
    5. In the Configure application parameters panel,
        DestinationArnType: Lambda - When the destination ARN for subscription filter is an AWS Lambda Function.
                         Kinesis - When the destination ARN for subscription filter is an Kinesis or Amazon Kinesis data firehose stream.
        DestinationArnValue: "Enter Destination ARN like Lambda function, Kinesis stream. For more information, visit - https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html
        LogGroupPattern: "Enter regex for matching logGroups"
        UseExistingLogs: "Select true for subscribing existing logs"
        LogGroupTags: "Enter comma separated keyvalue pairs for filtering logGroups using tags. Ex KeyName1=string,KeyName2=string. Supported only when UseExistingLogs is set to false.
        RoleArn: Enter AWS IAM Role arn in case the destination is Kinesis Firehose stream."
    6. Click Deploy.


### Configuring Lambda
#### Environment variables

**LOG_GROUP_PATTERN**: This JavaScript regex is used to filter log groups. Only log groups that match this pattern will be subscribed to the Lambda function. The default value is `Test`, which will match log groups like `testlogroup`, `logtestgroup`, and `LogGroupTest`.

##### Use Cases and it's Regex Pattern Example

| Case Description                                                     | Regex Pattern  Example              |
|----------------------------------------------------------------------|-------------------------------------|
| To subscribe all loggroup                                            | `/*` or (leave empty)               |
| To subscribe all loggroup paths only                                 | `/`                                 |
| To subscribe all loggroup of aws services                            | `/aws/*`                            |
| To subscribe to loggroups for only one service, such as Lambda       | `/aws/lambda/*`                     |
| To subscribe loggroup multiple services like lambda, rds, apigateway | `/aws/(lambda\|rds\|apigateway)`    |
| To subscribe loggroup by key word like `Test` or `Prod`              | `Test` or `Prod` [Case insensitive] |
| Don't subscribe if `LOG_GROUP_PATTERN`                               | `^$`                                |

**LOG_GROUP_TAGS**: This is used to filter log groups based on tags. Only log groups that match any of the specified key-value pairs will be subscribed to the Lambda function. It is case-sensitive.
#### e.g
```bash
LOG_GROUP_TAGS="Environment=Production,Application=MyApp"
```
> 💡 **Tip**: To filter log groups based on tags only, set `LOG_GROUP_PATTERN=^$`.

> **Note**: `LOG_GROUP_PATTERN` and `LOG_GROUP_TAGS` can be used together to subscribe to log groups or can be used separately.

**DESTINATION_ARN**: This specifies ARN of the Destination to Subscribe the log group. 

Lambda Destination ARN :- This specifies ARN of the Lambda function. Also you have to specify FunctionName attribute in your lambda function so that AWS does not generate random function name. This is to avoid making changes to the lambda function configuration in case your lambda function gets created again.

```
    {
        "Fn::Join": [
            "",
            [
              "arn:aws:lambda:",
              { "Ref" : "AWS::Region" },
              ":",
              { "Ref" : "AWS::AccountId" },
              ":function:<Your Lambda Function Name>"
            ]
        ]
    }
```

Kinesis Destination ARN :- This specifies the ARN of the kinesis Stream.

**ROLE_ARN** : This is used when subscription destination ARN is kinesis firehose stream.

### For Developers

Installing Dependencies. Test cases requires [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html), [BOTO3](https://pypi.org/project/boto3/), [CFN FLIP](https://pypi.org/project/cfn-flip/) and Requests python packages.

Running the test cases

```
  python test_loggroup_lambda_connector.py
```

## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues


