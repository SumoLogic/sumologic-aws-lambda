import unittest
import boto3
from time import sleep
import json
import os
import sys
import datetime

BUCKET_PREFIX = "appdevstore"


class TestLambda(unittest.TestCase):

    '''
        fail case newlgrp
        success case testlggrp
        already exists subscription filter idempotent
    '''
    ZIP_FILE = 'loggroup-lambda-connector.zip'
    AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    FILTER_NAME = 'SumoLGLBDFilter'

    def setUp(self):
        self.config = {
            'AWS_REGION_NAME': self.AWS_REGION
        }
        self.LOG_GROUP_NAME = 'testloggroup-%s' % (
            datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        # aws_access_key_id aws_secret_access_key
        self.stack_name = "TestLogGrpConnectorStack-%s" % (
            datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        self.cf = boto3.client('cloudformation',
                               self.config['AWS_REGION_NAME'])
        self.template_name = 'loggroup-lambda-cft.json'
        self.template_data = self._parse_template(self.template_name)
        # replacing prod zipfile location to test zipfile location
        self.template_data = self.template_data.replace("appdevzipfiles", BUCKET_PREFIX, 1)
        RUNTIME = "nodejs%s" % os.environ.get("NODE_VERSION", "10.x")
        self.template_data = self.template_data.replace("nodejs10.x", RUNTIME)

    def get_account_id(self):
        client = boto3.client("sts", self.config['AWS_REGION_NAME'])
        account_id = client.get_caller_identity()["Account"]
        return account_id

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

    def test_existing_logs(self):
        upload_code_in_S3(self.config['AWS_REGION_NAME'])
        self.template_data = self.template_data.replace("false", "true", 1)
        self.create_stack()
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.create_log_group(self.LOG_GROUP_NAME)
        self.assertTrue(self.check_subscription_filter_exists(
            self.LOG_GROUP_NAME, self.FILTER_NAME))

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
        test_lambda_name = "TestLambda-%s" % (
            datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        template_data['Resources']["SumoCWLambdaInvokePermission"]["DependsOn"] = ["TestLambda"]
        template_data['Resources']["TestLambda"] = {
            "Type": "AWS::Lambda::Function",
            "DependsOn": [
                "SumoLogGroupLambdaConnectorRole"
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
                        "SumoLogGroupLambdaConnectorRole",
                        "Arn"
                    ]
                },
                "FunctionName": test_lambda_name,
                "Timeout": 300,
                "Handler": "index.handler",
                "Runtime": "nodejs10.x",
                "MemorySize": 128
            }
        }

        lambda_arn = "arn:aws:lambda:%s:%s:function:%s" % (
            self.config["AWS_REGION_NAME"], self.get_account_id(),
            test_lambda_name)
        template_data["Parameters"]["LambdaARN"]["Default"] = lambda_arn
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
    return '%s-%s' % (BUCKET_PREFIX, region)


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
    key = os.path.basename(TestLambda.ZIP_FILE)
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), TestLambda.ZIP_FILE)
    s3.upload_file(os.path.join(__file__, filename), bucket_name, key,
                   ExtraArgs={'ACL': 'public-read'})


def prod_deploy():
    global BUCKET_PREFIX
    BUCKET_PREFIX = 'appdevzipfiles'
    upload_code_in_multiple_regions()
    print("Uploading template file in S3")
    s3 = boto3.client('s3', "us-east-1")
    filename = os.path.join('test', 'loggroup-lambda-cft.json')
    bucket_name = "appdev-cloudformation-templates"
    key = os.path.basename(filename)
    s3.upload_file(filename, bucket_name, key,
                   ExtraArgs={'ACL': 'public-read'})
    print("Deployment Successfull: ALL files copied to Sumocontent")


if __name__ == '__main__':

    if len(sys.argv) > 1:
        BUCKET_PREFIX = sys.argv.pop()

    # upload_code_in_multiple_regions()
    unittest.main()
