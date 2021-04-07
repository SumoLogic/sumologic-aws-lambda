import datetime
import os
import subprocess
import sys
import unittest

import boto3

# Update the below values in case the template locations are changed.
from sumologic import SumoLogic

GUARD_DUTY_BENCHMARK_TEMPLATE = "guarddutybenchmark/template_v2.yaml"
GUARD_DUTY_BENCHMARK_SAM_TEMPLATE = "guarddutybenchmark/packaged_v2.yaml"

GUARD_DUTY_TEMPLATE = "guardduty/template.yaml"
GUARD_DUTY_SAM_TEMPLATE = "guardduty/packaged.yaml"

# Update the below values with preferred bucket name and aws region.
BUCKET_NAME = ""
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
# Update the below values with preferred access id, access key and deployment
SUMO_ACCESS_ID = ""
SUMO_ACCESS_KEY = ""
SUMO_DEPLOYMENT = ""


def read_file(file_path):
    file_path = os.path.join(os.path.dirname(os.getcwd()), file_path)
    with open(file_path, "r") as f:
        return f.read().strip()


def create_sam_package_and_upload(template, packaged_template, bucket_prefix):
    template_file_path = os.path.join(os.path.dirname(os.getcwd()), template)
    packaged_template_path = os.path.join(os.path.dirname(os.getcwd()), packaged_template)

    # Create packaged template
    run_command(["sam", "package", "--template-file", template_file_path,
                 "--output-template-file", packaged_template_path, "--s3-bucket", BUCKET_NAME,
                 "--s3-prefix", bucket_prefix])
    # Upload the packaged template to S3
    upload_to_s3(packaged_template_path)


def upload_to_s3(file_path):
    print("Uploading %s file in S3 region: %s" % (file_path, AWS_REGION))
    s3 = boto3.client('s3', AWS_REGION)
    key = os.path.basename(file_path)
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
    s3.upload_file(os.path.join(__file__, filename), BUCKET_NAME, key, ExtraArgs={'ACL': 'public-read'})


def _run(command, input=None, check=False, **kwargs):
    if sys.version_info >= (3, 5):
        return subprocess.run(command, capture_output=True)
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
    resp = _run(cmdargs)
    if len(resp.stderr.decode()) > 0:
        # traceback.print_exc()
        raise Exception("Error in run command %s cmd: %s" % (resp, cmdargs))
    return resp.stdout


class SumoLogicResource(object):

    def __init__(self):
        self.sumo = SumoLogic(SUMO_ACCESS_ID, SUMO_ACCESS_KEY, self.api_endpoint)
        self.verificationErrors = []

    @property
    def api_endpoint(self):
        if SUMO_DEPLOYMENT == "us1":
            return "https://api.sumologic.com/api"
        elif SUMO_DEPLOYMENT in ["ca", "au", "de", "eu", "jp", "us2", "fed", "in"]:
            return "https://api.%s.sumologic.com/api" % SUMO_DEPLOYMENT
        else:
            return 'https://%s-api.sumologic.net/api' % SUMO_DEPLOYMENT

    def assert_collector(self, collector_id, assertions):
        collector_details = self.sumo.collector(collector_id)
        assertions(collector_details, assertions)

    def assert_httpsource(self, collector_id, source_id, assertions):
        source_details = self.sumo.source(collector_id, source_id)
        assertions(source_details, assertions)

    def assert_app(self, folder_id, assertions):
        folder_details = self.sumo.get_folder(folder_id)
        assertions(folder_details, assertions)

    def assertions(self, data, assertions):
        for key, value in assertions.items():
            try:
                assert value == data[key]
            except AssertionError as e:
                self.verificationErrors.append(str(e))


class CloudFormation(object):

    def __init__(self, name, template_path):
        self.cf = boto3.client('cloudformation', AWS_REGION)
        self.stack_name = "%s-%s" % (name, datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        self.template_data = read_file(template_path)
        self.outputs = {}
        self.resources = []

    def stack_exists(self):
        stacks = self.cf.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if self.stack_name == stack['StackName'] and stack['StackStatus'] == 'CREATE_COMPLETE':
                print("%s stack exists" % self.stack_name)
                stack_data = self.cf.describe_stacks(StackName=self.stack_name)
                outputs_stacks = stack_data["Stacks"][0]["Outputs"]
                for output in outputs_stacks:
                    self.outputs[output["OutputKey"]] = output["OutputValue"]
                self._fetch_resources()
                return True
        return False

    def _fetch_resources(self):
        response = []
        for page in self.cf.get_paginator("list_stack_resources").paginate(StackName=self.stack_name):
            response.extend(page["StackResourceSummaries"])
        if response:
            for resource in response:
                if "Custom::" in resource["ResourceType"]:
                    self.resources.append({
                        "Type": resource["ResourceType"].split("::")[1],
                        "Id": resource["PhysicalResourceId"].split("/")[1]
                    })

    def create_stack(self, parameters):
        params = {
            'StackName': self.stack_name,
            'TemplateBody': self.template_data,
            'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            'Parameters': self.create_stack_parameters(parameters)
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

    @staticmethod
    def create_stack_parameters(parameters_dict):
        parameters = []
        for key, value in parameters_dict:
            parameters.append({
                'ParameterKey': key,
                'ParameterValue': value
            })
        return parameters


class TestGuardDutyBenchmark(unittest.TestCase):

    def setUp(self):
        # Parameters
        self.collector_name = "Test GuardDuty Benchmark Lambda"
        self.source_name = "GuardDuty Benchmark"
        self.source_category = "Labs/test/guard/duty/benchmark"

        # Get GuardDuty details
        self.guard_duty = boto3.client('guardduty', AWS_REGION)
        response = self.guard_duty.list_detectors()
        if "DetectorIds" in response:
            self.detector_id = response["DetectorIds"][0]

        # Get CloudFormation client
        self.cf = CloudFormation("TestGuardDutyBenchmark", GUARD_DUTY_BENCHMARK_TEMPLATE)
        self.parameters = {
            "SumoDeployment": SUMO_DEPLOYMENT,
            "SumoAccessID": SUMO_ACCESS_ID,
            "SumoAccessKey": SUMO_ACCESS_KEY,
            "CollectorName": self.collector_name,
            "SourceName": self.source_name,
            "SourceCategoryName": self.source_category,
            "RemoveSumoResourcesOnDeleteStack": "true"
        }
        # Get Sumo Logic Client
        self.sumo_resource = SumoLogicResource()

    def tearDown(self):
        if self.cf.stack_exists():
            self.cf.delete_stack()

    def test_guard_duty_benchmark(self):
        self.cf.create_stack(self.parameters)
        print("Testing Stack Creation")
        self.assertTrue(self.cf.stack_exists())
        # Generate some sample findings
        self.guard_duty.create_sample_findings(DetectorId=self.detector_id)
        # Check if the app, collector and source is installed
        resources = sorted(self.cf.resources, key=lambda i: i['Type'])
        collector_id = ""
        for resource in resources:
            if resource['Type'] == 'Collector':
                self.sumo_resource.assert_collector(resource['Id'], {
                    "name": self.collector_name,
                    "collectorType": "Hosted"
                })
                collector_id = resource['Id']
            elif resource['Type'] == 'HTTPSource':
                self.sumo_resource.assert_httpsource(collector_id, resource['Id'], {
                    "name": self.source_name,
                    "category": self.source_category,
                    "sourceType": "HTTP"
                })
            elif resource['Type'] == 'App':
                self.sumo_resource.assert_app(resource['Id'], {
                    "name": "Global Intelligence for Amazon GuardDuty",
                    "itemType": "Folder"
                })
        # Go to SumoLogic and check if you received the logs
        # Assert one of the log for JSON format to check correctness


if __name__ == '__main__':
    unittest.main()
