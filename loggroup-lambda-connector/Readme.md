# SumoLogic LogGroup Connector
This is used to automatically subscribe newly created, newly tagged and existing Cloudwatch LogGroups to a Lambda function.

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
        LogGroupTags: "Enter comma separated keyvalue pairs for filtering logGroups using tags. Ex KeyName1=string,KeyName2=string. A logGroup is subscribed when it is created with a matching tag, or when a matching tag is added to it later, and unsubscribed when the matching tag is removed or changed (unless its name matches LogGroupPattern). With UseExistingLogs set to true, existing logGroups with a matching tag are subscribed as well.
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
#### For example
```bash
LOG_GROUP_TAGS="Environment=Production,Application=MyApp"
```
> 💡 **Tip**: To filter log groups based on tags only, set `LOG_GROUP_PATTERN=^$`.

> **Note**: `LOG_GROUP_PATTERN` and `LOG_GROUP_TAGS` can be used together to subscribe to log groups or can be used separately.

#### When a log group is subscribed or unsubscribed by its tags

| Situation | Result |
|-----------|--------|
| Log group is created with a matching tag | Yes |
| A matching tag is added to an existing log group later (`TagResource` or the deprecated `TagLogGroup`) | Yes, the log group's current tags are checked against `LOG_GROUP_TAGS` |
| `LOG_GROUP_TAGS` is changed and `UseExistingLogs` is `true` | Yes, the existing log groups are scanned again when the stack is updated |
| The matching tag is removed (`UntagResource` or the deprecated `UntagLogGroup`), or its value is changed so it no longer matches | **Unsubscribed**: the `SumoLGLBDFilter` subscription filter is deleted, unless the log group name still matches `LOG_GROUP_PATTERN` |
| The log group still has another tag that matches `LOG_GROUP_TAGS` | Stays subscribed |
| A log group name matches `LOG_GROUP_PATTERN` but only a tag was changed | Not subscribed because of the tag event. A name match alone subscribes only when the log group is created or during the existing log groups scan |

Tag matching is an exact, case-sensitive comparison of the key and the value. Entries without an `=` (for example a trailing comma) are ignored.

An unsubscribe is only done when all of these are true, otherwise the subscription is left as it is:
* `LOG_GROUP_TAGS` is not empty.
* The current tags of the log group could be read. A failed lookup (for example a permissions error or throttling) never counts as "no tags".
* The log group has a subscription filter named `SumoLGLBDFilter` whose destination is this connector's `DESTINATION_ARN`. Filters created by anyone or anything else are never deleted.

Unsubscribing stops sending that log group's new logs to Sumo Logic. Logs already ingested are not deleted. Changing `LOG_GROUP_TAGS` itself does not remove subscriptions that were made for the old tags.

> **Note**: Subscribing on a tag change relies on AWS CloudTrail recording CloudWatch Logs management events (`TagResource`, `TagLogGroup`, `UntagResource`, `UntagLogGroup`), the same as it does for `CreateLogGroup`. The log group is subscribed or unsubscribed within about a minute of the tag change.

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

### Required AWS permissions
The function role needs `logs:DescribeLogGroups`, `logs:DescribeLogStreams`, `logs:PutSubscriptionFilter`, `logs:ListTagsLogGroup`, `logs:DescribeSubscriptionFilters` and `logs:DeleteSubscriptionFilter`. The last two are used only to unsubscribe.

### Logs
The function writes its own logs to the `/aws/lambda/<function name>` CloudWatch log group (`Subscribing:`, `Unsubscribing:`, `Unmatched:`, `Not a log group event, ignoring:`). The log group name matches the default pattern `/aws/lambda`, so the connector can subscribe its own log group like any other.

### For Developers

Installing Dependencies. Test cases requires [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html), [BOTO3](https://pypi.org/project/boto3/), [CFN FLIP](https://pypi.org/project/cfn-flip/) and Requests python packages.

Running the test cases

The tests create real stacks and log groups in your AWS account and each one waits at least a minute, so a full run takes several minutes. Run them from the `test` directory, because the paths are built from its parent. The optional argument is the S3 bucket used by `sam package`.

```
  cd test
  python test_loggroup_lambda_connector.py [BUCKET_NAME]
```

Unit tests with the AWS SDK mocked need no AWS access:

```
  npm test
```

To run only the integration tests for tagging after creation and unsubscribing (no bucket argument when a test name is given):

```
  python test_loggroup_lambda_connector.py TestLambda.test_7_tag_added_after_creation
  python test_loggroup_lambda_connector.py TestLambda.test_8_deprecated_tag_log_group_after_creation
  python test_loggroup_lambda_connector.py TestLambda.test_9_non_matching_tag_is_not_subscribed
  python test_loggroup_lambda_connector.py TestLambda.test_10_removing_the_tag_unsubscribes
  python test_loggroup_lambda_connector.py TestLambda.test_11_changing_the_tag_value_unsubscribes
  python test_loggroup_lambda_connector.py TestLambda.test_12_removing_the_tag_keeps_a_name_matched_subscription
```

## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues


