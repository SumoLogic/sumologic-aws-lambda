import unittest
import boto3
from time import sleep
import json
import os


class TestLambda(unittest.TestCase):

    '''
        fail case newlgrp
        success case testlggrp
        already exists subscription filter idempotent
        manually test inserting logs in newloggrp executes sumocwl lambda
    '''

    ZIP_FILE = 'loggroup-lambda-connector.zip'
    ZIP_FILE_S3BUCKET = 'appdevfiles'
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
        self.upload_code_in_S3()
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

    def _parse_template(self, template):
        with open(template) as template_fileobj:
            template_data = template_fileobj.read()
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        return template_data

    def upload_code_in_S3(self):
        print("Uploading zip file in S3")
        s3 = boto3.client('s3', self.config['AWS_REGION_NAME'])
        s3.upload_file(self.ZIP_FILE, self.ZIP_FILE_S3BUCKET, self.ZIP_FILE)


if __name__ == '__main__':
    unittest.main()
