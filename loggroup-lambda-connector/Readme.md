# LogGroup Lambda Connector
This is used to automatically subscribe newly created Cloudwatch LogGroups to a Lambda function.

### Prerequisites

```
    npm install
```

### Building


```
    npm run build
```
Upload the generated loggroup-lambda-connector.zip in S3 bucket(specify it's bucket and key in cloudformation template default is  bucketname: appdevstore and key: loggroup-lambda-connector.zip).

### Creating Stack in AWS Cloudformation
you can create the stack by using [aws-cli](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-cli-creating-stack.html) or directly from aws console using webbrowser and uploading loggroup-lambda-cft.json.


### Running Test Cases
Run the following command after building the zip file
```
    python test_loggroup_lambda_connector.py
```

### Configuring Lambda
It has two environment variables

**LOG_GROUP_PATTERN**: This is a javascript regex to filter out loggroups. Only loggroups which match this pattern will be subscribed to the lambda function.Do not use '/' while writing the pattern and it is case insensitive.

```
    Test - will match testlogroup, logtestgroup and LogGroupTest
```

**LAMBDA_ARN**: This specifies ARN of the lambda functions. Also you have to specify FunctionName attribute in your lambda function so that AWS does not generate random function name.This is to avoid making changes to the lambda function configuration in case your lambda function gets created again.

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


