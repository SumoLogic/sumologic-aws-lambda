import unittest
import boto3
from time import sleep, time
import json
import os


class TestLambda(unittest.TestCase):

    '''
        fail case newlgrp
        success case testlggrp
        already exists subscription filter idempotent
    '''

    ZIP_FILE = 'loggroup-lambda-connector.zip'
    ZIP_FILE_S3BUCKET = 'appdevzipfiles'
    AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
    FILTER_NAME = 'SumoLGLBDFilter'
    LOG_GROUP_NAME = 'testloggroup'
    FUNCTION_NAME = 'SumoLogGroupLambdaConnector'

    def setUp(self):
        self.config = {
            'AWS_REGION_NAME': self.AWS_REGION
        }
        # aws_access_key_id aws_secret_access_key
        self.stack_name = "TestLogGrpConnectorStack"
        self.cf = boto3.client('cloudformation',
                               self.config['AWS_REGION_NAME'])
        self.template_name = 'loggroup-lambda-cft.json'
        self.template_data = self._parse_template(self.template_name)

    def tearDown(self):
        if self.stack_exists(self.stack_name):
            self.delete_stack()
        self.delete_log_group(self.LOG_GROUP_NAME)

    def test_lambda(self):
        upload_code_in_S3(self.config['AWS_REGION_NAME'])
        self.create_stack()
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.create_log_group(self.LOG_GROUP_NAME)
        self.assertTrue(self.check_subscription_filter_exists(
            self.LOG_GROUP_NAME, self.FILTER_NAME))
        # self.invoke_lambda()

    def stack_exists(self, stack_name):
        stacks = self.cf.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName'] and stack['StackStatus'] == 'CREATE_COMPLETE':
                print("%s stack exists" % stack_name)
                return True
        return False

    def create_stack(self):
        params = {
            'StackName': self.stack_name,
            'TemplateBody': self.template_data,
            'Capabilities': ['CAPABILITY_IAM']
        }
        stack_result = self.cf.create_stack(**params)
        print('Creating {}'.format(self.stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=self.stack_name)

    def delete_stack(self):
        params = {
            'StackName': self.stack_name
        }
        stack_result = self.cf.delete_stack(**params)
        print('Deleting {}'.format(self.stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_delete_complete')
        print("...waiting for stack to be removed...")
        waiter.wait(StackName=self.stack_name)

    def invoke_lambda(self):
        event = {
            "version": "0",
            "id": "ff981fd2-86ad-fe82-b335-01820bf26c54",
            "detail-type": "AWS API Call via CloudTrail",
            "source": "aws.logs",
            "account": "1234567890",
            "time": "2017-12-22T18:58:21Z",
            "region": "us-east-2",
            "resources": [],
            "detail": {
                "eventVersion": "1.04",
                "userIdentity": {
                    "type": "AssumedRole",
                    "principalId": "ABCDEFABCDEFABCDEF",
                    "arn": "arn:aws:sts::1234567890:userArn",
                    "accountId": "844560495595",
                    "accessKeyId": "ABCDEFABCDEFABCDEF",
                    "sessionContext": "[Object]"
                },
                "eventTime": "2017-12-22T18:58:21Z",
                "eventSource": "logs.amazonaws.com",
                "eventName": "CreateLogGroup",
                "awsRegion": "us-east-2",
                "sourceIPAddress": "205.251.233.181",
                "userAgent": "AWS CloudWatch Console",
                "requestParameters": {"logGroupName": self.LOG_GROUP_NAME},
                "eventName": "CreateLogGroup",
                "responseElements": "null",
                "requestID": "1444d21e-e74a-11e7-b865-1f3862c7419e",
                "eventID": "e1b43cd9-2683-4258-b1a8-9c248947372b",
                "eventType": "AwsApiCall",
                "apiVersion": "20140328"
            }
        }
        lambda_client = boto3.client('lambda', self.config['AWS_REGION_NAME'])
        response = lambda_client.invoke(FunctionName=self.FUNCTION_NAME,
                                        Payload=json.dumps(event))
        print("Invoking lambda function", response)

    def delete_log_group(self, log_group_name):
        cwlclient = boto3.client('logs', self.config['AWS_REGION_NAME'])
        response = cwlclient.delete_log_group(logGroupName=log_group_name)
        print("deleting log group", response)

    def create_log_group(self, log_group_name):
        cwlclient = boto3.client('logs', self.config['AWS_REGION_NAME'])
        response = cwlclient.create_log_group(logGroupName=log_group_name)
        print("creating log group", response)

    def check_subscription_filter_exists(self, log_group_name, filter_name):
        sleep(60)
        cwlclient = boto3.client('logs', self.config['AWS_REGION_NAME'])
        response = cwlclient.describe_subscription_filters(
            logGroupName=log_group_name,
            filterNamePrefix=filter_name
        )
        print("testing subscription filter exists", response)
        if len(response['subscriptionFilters']) > 0 and response['subscriptionFilters'][0]['filterName'] == filter_name:
            return True
        else:
            return False

    def add_dummy_lambda(self, template_data):
        template_data = eval(template_data)
        template_data['Resources']["TestLambda"] = {
            "Type": "AWS::Lambda::Function",
            "DependsOn": [
                "SumoLGCnLambdaExecutionRole"
            ],
            "Properties": {
                "Code": {
                    "ZipFile": {"Fn::Join": ["", [
                        "exports.handler = function(event, context) {",
                        "console.log('Success');",
                        "};"
                    ]]}
                },
                "Role": {
                    "Fn::GetAtt": [
                        "SumoLGCnLambdaExecutionRole",
                        "Arn"
                    ]
                },
                "FunctionName": "TestLambda",
                "Timeout": 300,
                "Handler": "index.handler",
                "Runtime": "nodejs4.3",
                "MemorySize": 128
            }
        }
        template_data['Resources']['SumoLGCnLambdaPermission'] = {
            "Type": "AWS::Lambda::Permission",
            "Properties": {
                "FunctionName": {
                    "Fn::GetAtt": [
                        "TestLambda",
                        "Arn"
                    ]
                },
                "Action": "lambda:InvokeFunction",
                "Principal": {"Fn::Join": [".",
                                           ["logs", {"Ref": "AWS::Region"},
                                            "amazonaws.com"]
                                           ]},
                "SourceAccount": {"Ref": "AWS::AccountId"}
            }
        }
        template_data = str(template_data)
        return template_data

    def _parse_template(self, template):
        with open(template) as template_fileobj:
            template_data = template_fileobj.read()

        template_data = self.add_dummy_lambda(template_data)
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        return template_data


def upload_code_in_multiple_regions():
    regions = [
        "us-east-2",
        "us-east-1",
        "us-west-1",
        "us-west-2",
        "ap-south-1",
        "ap-northeast-2",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "ca-central-1",
    # "cn-north-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "sa-east-1"
    ]

    # for region in regions:
    #     create_bucket(region)

    for region in regions:
        upload_code_in_S3(region)


def get_bucket_name(region):
    return '%s-%s' % (TestLambda.ZIP_FILE_S3BUCKET, region)


def create_bucket(region):
    s3 = boto3.client('s3', region)
    bucket_name = get_bucket_name(region)
    if region == "us-east-1":
        response = s3.create_bucket(Bucket=bucket_name)
    else:
        response = s3.create_bucket(Bucket=bucket_name,
                                    CreateBucketConfiguration={
                                        'LocationConstraint': region
                                    })
    print("Creating bucket", region, response)


def upload_code_in_S3(region):
    print("Uploading zip file in S3 region: %s" % region)
    s3 = boto3.client('s3', region)
    bucket_name = get_bucket_name(region)
    filename = TestLambda.ZIP_FILE
    s3.upload_file(filename, bucket_name, filename,
                   ExtraArgs={'ACL': 'public-read'})


if __name__ == '__main__':
    # upload_code_in_multiple_regions()
    unittest.main()
