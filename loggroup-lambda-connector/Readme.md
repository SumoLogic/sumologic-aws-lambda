# SumoLogic LogGroup Connector
This is used to automatically subscribe newly created and existing Cloudwatch LogGroups to a Lambda function.

Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)

### Deploying the SAM Application
    1. Open a browser window and enter the following URL: https://serverlessrepo.aws.amazon.com/applications
    2. In the Serverless Application Repository, search for sumologic.
    3. Select Show apps that create custom IAM roles or resource policies check box.
    4. Click the sumologic-loggroup-connector,link, and then click Deploy.
    5. In the Configure application parameters panel,
        LambdaARN: "Enter ARN for target lambda function" All loggroups matching the pattern are subscribed to this function
        LogGroupPattern: "Enter regex for matching logGroups"
        UseExistingLogs: "Select true for subscribing existing logs"
        LogGroupTags: "Enter comma separated keyvalue pairs for filtering logGroups using tags. Ex KeyName1=string,KeyName2=string. Supported only when UseExistingLogs is set to false."
    6. Click Deploy.


### Configuring Lambda
It has two environment variables

**LOG_GROUP_PATTERN**: This is a javascript regex to filter out loggroups. Only loggroups which match this pattern will be subscribed to the lambda function.Do not use '/' while writing the pattern and it is case insensitive.

```
    Test - will match testlogroup, logtestgroup and LogGroupTest
```

**LAMBDA_ARN**: This specifies ARN of the lambda functions. Also you have to specify FunctionName attribute in your lambda function so that AWS does not generate random function name. This is to avoid making changes to the lambda function configuration in case your lambda function gets created again.

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

**USE_EXISTING_LOGS**: This is used for subscribing existing log groups. By setting this parameter to true and invoking the function manually, all the existing log groups matching the pattern will be subscribed to lambda function with `LAMBDA_ARN` as arn

**LogGroupTags**: This is used for filtering out loggroups based on tags.Only loggroups which match any one of the key value pairs will be subscribed to the lambda function. This works only for new loggroups not existing loggroups.

### For Developers

Installing Dependencies
```
  npm install
```

Building zip file
```
  npm run build
```
Upload the generated loggroup-lambda-connector.zip in S3 bucket(don't forget to change bucket name and key in cloudformation template)

Running the test cases

```
  python test_loggroup_lambda_connector.py
```
Run the above command after building the zip file

## License

Apache License 2.0 (Apache-2.0)


## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues


