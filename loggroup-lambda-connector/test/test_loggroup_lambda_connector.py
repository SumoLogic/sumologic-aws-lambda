import subprocess
import time
import unittest
import boto3
from time import sleep
import json
import os
import sys
import datetime

import cfn_flip

# Modify the name of the bucket prefix for testing
BUCKET_PREFIX = "appdevstore"
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


class TestLambda(unittest.TestCase):
    '''
        fail case newlgrp
        success case testlggrp
        already exists subscription filter idempotent
    '''

    def setUp(self):
        # Set Up AWS Clients
        self.log_group_client = boto3.client('logs', AWS_REGION)
        self.cf = boto3.client('cloudformation', AWS_REGION)
        self.lambda_cl = boto3.client('lambda', AWS_REGION)

        # AWS Resource Names
        self.log_group_name = 'testloggroup-%s' % (datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        self.stack_name = "TestLogGrpConnectorStack-%s" % (datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))

        self.bucket_name = get_bucket_name()
        self.outputs = {}
        # Read template
        self.template_data = read_file("test/test-template.yaml")

    def tearDown(self):
        if self.stack_exists(self.stack_name):
            self.delete_stack(self.stack_name)
        self.delete_log_group()

    def test_1_lambda(self):
        self.create_stack(self.stack_name, self.template_data, self.create_stack_parameters("Lambda", "false"))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.create_log_group()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def test_2_existing_logs(self):
        self.create_log_group()
        self.create_stack(self.stack_name, self.template_data, self.create_stack_parameters("Lambda", "true"))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        #self.invoke_lambda()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def test_3_kinesis(self):
        self.create_stack(self.stack_name, self.template_data, self.create_stack_parameters("Kinesis", "false"))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.create_log_group()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def test_4_existing_kinesis(self):
        self.create_log_group()
        self.create_stack(self.stack_name, self.template_data, self.create_stack_parameters("Kinesis", "true"))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        #self.invoke_lambda()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def test_5_matching_existing_loggroup_with_pattern_and_tag(self):
        self.create_log_group_with_tag()
        self.create_stack(self.stack_name, self.template_data,
                          self.create_stack_parameters("Kinesis","true", loggroup_tag='env=prod'))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        #self.invoke_lambda()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def test_6_matching_existing_loggroup_by_tag_only(self):
        self.create_log_group_with_tag()
        self.create_stack(self.stack_name, self.template_data,
                          self.create_stack_parameters("Kinesis","true", loggroup_pattern='^$',
                                                       loggroup_tag='username=akhil'))
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        #self.invoke_lambda()
        self.assert_subscription_filter("SumoLGLBDFilter")

    def create_stack_parameters(self, destination, existing, loggroup_pattern='test', loggroup_tag=''):
        return [
            {
                'ParameterKey': 'DestinationType',
                'ParameterValue': destination
            },
            {
                'ParameterKey': 'LogGroupPattern',
                'ParameterValue': loggroup_pattern
            },
            {
                'ParameterKey': 'LogGroupTags',
                'ParameterValue': loggroup_tag
            },
            {
                'ParameterKey': 'UseExistingLogs',
                'ParameterValue': existing
            },
            {
                'ParameterKey': 'BucketName',
                'ParameterValue': self.bucket_name
            }
        ]

    def stack_exists(self, stack_name):
        stacks = self.cf.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName'] and stack['StackStatus'] == 'CREATE_COMPLETE':
                print("%s stack exists" % stack_name)
                stack_data = self.cf.describe_stacks(StackName=self.stack_name)
                outputs_stacks = stack_data["Stacks"][0]["Outputs"]
                for output in outputs_stacks:
                    self.outputs[output["OutputKey"]] = output["OutputValue"]
                return True
        return False

    def create_stack(self, stack_name, template_data, parameters):
        params = {
            'StackName': stack_name,
            'TemplateBody': template_data,
            'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            'Parameters': parameters
        }
        stack_result = self.cf.create_stack(**params)
        print('Creating {}'.format(stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=stack_name)

    def delete_stack(self, stack_name):
        params = {
            'StackName': stack_name
        }
        stack_result = self.cf.delete_stack(**params)
        print('Deleting {}'.format(stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_delete_complete')
        print("...waiting for stack to be removed...")
        waiter.wait(StackName=stack_name)

    def delete_log_group(self):
        response = self.log_group_client.delete_log_group(logGroupName=self.log_group_name)
        print("deleting log group", response)

    def create_log_group(self):
        response = self.log_group_client.create_log_group(logGroupName=self.log_group_name)
        print("creating log group", response)

    def create_log_group_with_tag(self):
        tags = {
            'team': 'apps',
            'env': 'prod'
        }
        self.log_group_name = 'mytag-%s' % (datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        print("Loggroup Name", self.log_group_name)
        response = self.log_group_client.create_log_group(logGroupName=self.log_group_name, tags=tags)
        print("creating log group", response)

    def assert_subscription_filter(self, filter_name):
        sleep(60)
        response = self.log_group_client.describe_subscription_filters(
            logGroupName=self.log_group_name,
            filterNamePrefix=filter_name
        )
        print("testing subscription filter exists", response)
        # Add multiple assert for name, destination arn, role arn.
        assert len(response['subscriptionFilters']) > 0
        assert response['subscriptionFilters'][0]['filterName'] == filter_name
        assert response['subscriptionFilters'][0]['logGroupName'] == self.log_group_name
        assert response['subscriptionFilters'][0]['destinationArn'] == self.outputs["destinationArn"]
        if "roleArn" in self.outputs:
            assert response['subscriptionFilters'][0]['roleArn'] == self.outputs["roleArn"]

    def _parse_template(self, template_name):
        output_file = cfn_flip.to_json(read_file(template_name))
        template_data = json.loads(output_file)
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        return template_data

    def invoke_lambda(self):
        lambda_arn = self.outputs["LambdaARN"]
        output = self.lambda_cl.invoke(
            FunctionName=lambda_arn,
            InvocationType='Event',
            LogType='None',
            Payload=bytes(json.dumps({"value": "test"}), "utf-8")
        )
        if output["StatusCode"] != 202:
            raise Exception("Failed to invoke Lambda")
        time.sleep(60)


def read_file(file_path):
    file_path = os.path.join(os.path.dirname(os.getcwd()), file_path)
    with open(file_path, "r") as f:
        return f.read().strip()


def get_bucket_name():
    return '%s-%s' % (BUCKET_PREFIX, AWS_REGION)


def upload_to_s3(file_path):
    print("Uploading %s file in S3 region: %s" % (file_path, AWS_REGION))
    s3 = boto3.client('s3', AWS_REGION)
    bucket_name = get_bucket_name()
    key = os.path.basename(file_path)
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    s3.upload_file(os.path.join(__file__, filename), bucket_name, key, ExtraArgs={'ACL': 'public-read'})


def create_sam_package_and_upload():
    template_file_path = os.path.join(os.path.dirname(os.getcwd()), "sam/template.yaml")
    packaged_template_path = os.path.join(os.path.dirname(os.getcwd()), "sam/packaged.yaml")

    # Create packaged template
    run_command(["sam", "package", "--template-file", template_file_path,
                 "--output-template-file", packaged_template_path, "--s3-bucket", get_bucket_name(),
                 "--s3-prefix", "test-log-group-lambda-connector"])
    # Upload the packaged template to S3
    upload_to_s3(packaged_template_path)


def _run(command, input=None, check=False, **kwargs):
    if sys.version_info >= (3, 5):
        result = subprocess.run(command, capture_output=True)
        return result.returncode, result.stdout, result.stderr
    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE

    process = subprocess.Popen(command, **kwargs)
    try:
        stdout, stderr = process.communicate(input)
    except:
        process.kill()
        process.wait()
        raise
    retcode = process.poll()
    if check and retcode:
        raise subprocess.CalledProcessError(
            retcode, process.args, output=stdout, stderr=stderr)
    return retcode, stdout, stderr


def run_command(cmdargs):
    retcode, stdout, stderr = _run(cmdargs)
    if retcode != 0:
        # traceback.print_exc()
        raise Exception("Error in run command %s cmd: %s" % (stderr, cmdargs))
    return retcode, stdout, stderr


if __name__ == '__main__':

    if len(sys.argv) > 1:
        BUCKET_PREFIX = sys.argv.pop()
    create_sam_package_and_upload()
    # upload_code_in_multiple_regions()
    # Run the test cases
    unittest.main()
