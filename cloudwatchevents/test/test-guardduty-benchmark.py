import copy
import datetime
import json
import os
import subprocess
import sys
import time
import unittest

import boto3
from sumologic import SumoLogic

# Update the below values in case the template locations are changed.

GUARD_DUTY_BENCHMARK_TEMPLATE = "guarddutybenchmark/template_v2.yaml"
GUARD_DUTY_BENCHMARK_SAM_TEMPLATE = "guarddutybenchmark/packaged_v2.yaml"

GUARD_DUTY_TEMPLATE = "guardduty/template.yaml"
GUARD_DUTY_SAM_TEMPLATE = "guardduty/packaged.yaml"

CLOUDWATCH_TEMPLATE = "guardduty/cloudwatchevents.json"

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
    print("Generating SAM package for the template %s at location %s." % (template, packaged_template))
    template_file_path = os.path.join(os.path.dirname(os.getcwd()), template)
    packaged_template_path = os.path.join(os.path.dirname(os.getcwd()), packaged_template)

    # Create packaged template
    run_command(["sam", "package", "--template-file", template_file_path,
                 "--output-template-file", packaged_template_path, "--s3-bucket", BUCKET_NAME,
                 "--s3-prefix", bucket_prefix])
    print("Generation complete for SAM template %s with files uploaded to Bucket %s, Prefix %s." % (
        packaged_template, BUCKET_NAME, bucket_prefix))


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
    if resp.returncode != 0:
        # traceback.print_exc()
        raise Exception("Error in run command %s cmd: %s" % (resp, cmdargs))
    return resp.stdout


class SumoLogicResource(object):

    def __init__(self, source_category, finding_types, delay):
        print("Initializing SumoLogicResource Object.")
        self.sumo = SumoLogic(SUMO_ACCESS_ID, SUMO_ACCESS_KEY, self.api_endpoint)
        self.verificationErrors = []
        self.delay = delay
        self.source_category = source_category
        self.findings = copy.deepcopy(finding_types)
        self.findings.append("CreateSampleFindings")
        print("Initialization complete for SumoLogicResource Object.")

    @property
    def api_endpoint(self):
        if SUMO_DEPLOYMENT == "us1":
            return "https://api.sumologic.com/api"
        elif SUMO_DEPLOYMENT in ["ca", "au", "de", "eu", "jp", "us2", "fed", "in"]:
            return "https://api.%s.sumologic.com/api" % SUMO_DEPLOYMENT
        else:
            return 'https://%s-api.sumologic.net/api' % SUMO_DEPLOYMENT

    def create_collector(self, collector_name):
        collector = {
            'collector': {
                'collectorType': "Hosted",
                'name': collector_name,
                'description': "This is a test collector."
            }
        }
        response_collector = self.sumo.create_collector(collector, headers=None)
        return json.loads(response_collector.text)

    def create_source(self, collector_id, source_name):
        source_json = {
            "source":
                {
                    "name": source_name,
                    "category": self.source_category,
                    "automaticDateParsing": True,
                    "multilineProcessingEnabled": True,
                    "useAutolineMatching": True,
                    "forceTimeZone": False,
                    "defaultDateFormats": [{
                        "format": "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
                        "locator": ".*\"updatedAt\":\"(.*)\".*"
                    }],
                    "filters": [],
                    "cutoffTimestamp": 0,
                    "encoding": "UTF-8",
                    "fields": {

                    },
                    "messagePerRequest": False,
                    "sourceType": "HTTP"
                }
        }
        response_source = self.sumo.create_source(collector_id, source_json)
        return json.loads(response_source.text)

    def delete_collector(self, collector):
        try:
            self.sumo.delete_collector(collector)
        except Exception as e:
            print(e)

    def delete_source(self, collector_id, source):
        try:
            self.sumo.delete_source(collector_id, source)
        except Exception as e:
            print(e)

    def fetch_logs(self):
        raw_messages = []
        # fetch Last 10 Minutes logs
        to_time = int(time.time()) * 1000
        from_time = to_time - self.delay * 60 * 1000
        search_query = '_sourceCategory=%s' % self.source_category
        search_job_response = self.sumo.search_job(search_query, fromTime=from_time, toTime=to_time, timeZone="IST")
        print("Search Jobs API success with JOB ID as %s." % search_job_response["id"])
        state = "GATHERING RESULTS"
        message_count = 0
        while state == "GATHERING RESULTS":
            response = self.sumo.search_job_status(search_job_response)
            if response and "state" in response:
                state = response["state"]
                if state == "DONE GATHERING RESULTS":
                    message_count = response["messageCount"]
                elif state != "GATHERING RESULTS":
                    state = "EXIT"
                else:
                    time.sleep(2)
        if message_count != 0:
            messages = self.sumo.search_job_messages(search_job_response, message_count, 0)
            if messages and "messages" in messages:
                messages = messages["messages"]
                for message in messages:
                    if "map" in message and "_raw" in message["map"]:
                        raw_messages.append(json.loads(message["map"]["_raw"]))
        print("Received message count as %s." % len(raw_messages))
        return raw_messages

    # Validate the specific findings generated
    def assert_logs(self):
        messages = self.fetch_logs()
        for finding_type in self.findings:
            try:
                assert any((("type" in d and d["type"] == finding_type)
                            or ("eventName" in d and d["eventName"] == finding_type)) for d in messages)
            except AssertionError as e:
                self.verificationErrors.append(
                    "Finding Type \" %s \" not found in the Logs fetched from Sumo Logic." % finding_type)

    def assert_collector(self, collector_id, assertions):
        collector_details, etag = self.sumo.collector(collector_id)
        self.assertions(collector_details['collector'], assertions)

    def assert_httpsource(self, collector_id, source_id, assertions):
        source_details, etag = self.sumo.source(collector_id, source_id)
        self.assertions(source_details['source'], assertions)

    def assert_app(self, folder_id, assertions):
        folder_details = self.sumo.get_folder(folder_id)
        self.assertions(json.loads(folder_details.text), assertions)

    def assertions(self, data, assertions):
        for key, value in assertions.items():
            try:
                assert value == data[key] or value in data[key]
            except AssertionError as e:
                self.verificationErrors.append(
                    "Expected Value \" %s \" does not match the current value \" %s \" for the Key "
                    "as \" %s \"." % (value, data[key], key))


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
                print("%s stack exists." % self.stack_name)
                stack_data = self.cf.describe_stacks(StackName=self.stack_name)
                outputs_stacks = stack_data["Stacks"][0]["Outputs"]
                for output in outputs_stacks:
                    self.outputs[output["OutputKey"]] = output["OutputValue"]
                print("Fetched Outputs from Stack.")
                self._fetch_resources()
                print("Fetched Resources from Stack.")
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
        print('Creating {}.'.format(self.stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=self.stack_name)

    def delete_stack(self):
        params = {
            'StackName': self.stack_name
        }
        stack_result = self.cf.delete_stack(**params)
        print('Deleting {}.'.format(self.stack_name), stack_result)
        waiter = self.cf.get_waiter('stack_delete_complete')
        print("...waiting for stack to be removed...")
        waiter.wait(StackName=self.stack_name)

    @staticmethod
    def create_stack_parameters(parameters_dict):
        parameters = []
        for key, value in parameters_dict.items():
            parameters.append({
                'ParameterKey': key,
                'ParameterValue': value
            })
        return parameters


class TestGuardDutyBenchmark(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestGuardDutyBenchmark, cls).setUpClass()
        create_sam_package_and_upload(GUARD_DUTY_BENCHMARK_TEMPLATE, GUARD_DUTY_BENCHMARK_SAM_TEMPLATE,
                                      "guarddutybenchmark")
        print("Completed SetUp for All test Cases.")

    def setUp(self):
        # Parameters
        self.collector_name = "Test GuardDuty Benchmark Lambda"
        self.source_name = "GuardDuty Benchmark"
        self.source_category = "Labs/test/guard/duty/benchmark"
        self.finding_types = ["Policy:S3/AccountBlockPublicAccessDisabled", "Policy:S3/BucketPublicAccessGranted"]
        self.delay = 7

        # Get GuardDuty details
        self.guard_duty = boto3.client('guardduty', AWS_REGION)
        response = self.guard_duty.list_detectors()
        if "DetectorIds" in response:
            self.detector_id = response["DetectorIds"][0]

        # Get CloudFormation client
        self.cf = CloudFormation("TestGuardDutyBenchmark", GUARD_DUTY_BENCHMARK_SAM_TEMPLATE)
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
        self.sumo_resource = SumoLogicResource(self.source_category, self.finding_types, self.delay)

    def tearDown(self):
        if self.cf.stack_exists():
            self.cf.delete_stack()

    def test_guard_duty_benchmark(self):
        self.cf.create_stack(self.parameters)
        print("Testing Stack Creation.")
        self.assertTrue(self.cf.stack_exists())
        # Generate some specific sample findings
        print("Generating sample GuardDuty findings.")
        self.guard_duty.create_sample_findings(DetectorId=self.detector_id, FindingTypes=self.finding_types)
        # Check if the app, collector and source is installed
        print("Validate Collector, source and app.")
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
        print("Waiting for %s minutes for logs to appear in Sumo Logic." % self.delay)
        time.sleep(self.delay * 60)
        # Go to SumoLogic and check if you received the logs
        # Assert one of the log for JSON format to check correctness
        print("Validate Logs in Sumo Logic.")
        self.sumo_resource.assert_logs()

        if len(self.sumo_resource.verificationErrors) > 0:
            print("Assertions failures are:- %s." % '\n'.join(self.sumo_resource.verificationErrors))
            assert len(self.sumo_resource.verificationErrors) == 0


class TestGuardDuty(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestGuardDuty, cls).setUpClass()
        create_sam_package_and_upload(GUARD_DUTY_TEMPLATE, GUARD_DUTY_SAM_TEMPLATE,
                                      "guardduty")
        print("Completed SetUp for All test Cases.")

    def setUp(self):
        # Parameters
        self.collector_name = "Test GuardDuty Lambda"
        self.source_name = "GuardDuty"
        self.source_category = "Labs/test/guard/duty"
        self.finding_types = ["DefenseEvasion:IAMUser/AnomalousBehavior", "Backdoor:EC2/Spambot"]
        self.delay = 7

        # Get GuardDuty details
        self.guard_duty = boto3.client('guardduty', AWS_REGION)
        response = self.guard_duty.list_detectors()
        if "DetectorIds" in response:
            self.detector_id = response["DetectorIds"][0]

        # Get Sumo Logic Client
        self.sumo_resource = SumoLogicResource(self.source_category, self.finding_types, self.delay)
        # Create a collector and http source for testing
        self.collector = self.sumo_resource.create_collector(self.collector_name)
        self.collector_id = self.collector['collector']['id']
        self.source = self.sumo_resource.create_source(self.collector_id, self.source_name)
        self.source_id = self.source['source']['id']

        # Get CloudFormation client
        self.cf = CloudFormation("TestGuardDuty", GUARD_DUTY_SAM_TEMPLATE)
        self.parameters = {
            "SumoEndpointUrl": self.source['source']['url'],
        }

    def tearDown(self):
        if self.cf.stack_exists():
            self.cf.delete_stack()
        self.sumo_resource.delete_source(self.collector_id, self.source)
        self.sumo_resource.delete_collector(self.collector)

    def test_guard_duty(self):
        self.cf.create_stack(self.parameters)
        print("Testing Stack Creation.")
        self.assertTrue(self.cf.stack_exists())
        # Generate some specific sample findings
        print("Generating sample GuardDuty findings.")
        self.guard_duty.create_sample_findings(DetectorId=self.detector_id, FindingTypes=self.finding_types)
        print("Waiting for %s minutes for logs to appear in Sumo Logic." % self.delay)
        time.sleep(self.delay * 60)
        # Go to SumoLogic and check if you received the logs
        # Assert one of the log for JSON format to check correctness
        print("Validate Logs in Sumo Logic.")
        self.sumo_resource.assert_logs()

        if len(self.sumo_resource.verificationErrors) > 0:
            print("Assertions failures are:- %s." % '\n'.join(self.sumo_resource.verificationErrors))
            assert len(self.sumo_resource.verificationErrors) == 0


class TestCloudWatchEvents(unittest.TestCase):

    def setUp(self):
        # Parameters
        self.collector_name = "Test CloudWatch Events Lambda"
        self.source_name = "CloudWatch Events"
        self.source_category = "Labs/test/cloudwatch/events"
        self.finding_types = ["Recon:IAMUser/MaliciousIPCaller.Custom", "Discovery:S3/TorIPCaller"]
        self.delay = 7

        # Get GuardDuty details
        self.guard_duty = boto3.client('guardduty', AWS_REGION)
        response = self.guard_duty.list_detectors()
        if "DetectorIds" in response:
            self.detector_id = response["DetectorIds"][0]

        # Get Sumo Logic Client
        self.sumo_resource = SumoLogicResource(self.source_category, self.finding_types, self.delay)
        # Create a collector and http source for testing
        self.collector = self.sumo_resource.create_collector(self.collector_name)
        self.collector_id = self.collector['collector']['id']
        self.source = self.sumo_resource.create_source(self.collector_id, self.source_name)
        self.source_id = self.source['source']['id']

        # Get CloudFormation client
        self.cf = CloudFormation("TestCloudWatchEvents", CLOUDWATCH_TEMPLATE)
        self.parameters = {
            "SumoEndpointUrl": self.source['source']['url'],
        }

    def tearDown(self):
        if self.cf.stack_exists():
            self.cf.delete_stack()
        self.sumo_resource.delete_source(self.collector_id, self.source)
        self.sumo_resource.delete_collector(self.collector)

    def test_cloudwatch_event(self):
        self.cf.create_stack(self.parameters)
        print("Testing Stack Creation.")
        self.assertTrue(self.cf.stack_exists())
        # Generate some specific sample findings
        print("Generating sample CloudWatch Events.")
        self.guard_duty.create_sample_findings(DetectorId=self.detector_id, FindingTypes=self.finding_types)
        print("Waiting for %s minutes for logs to appear in Sumo Logic." % self.delay)
        time.sleep(self.delay * 60)
        # Go to SumoLogic and check if you received the logs
        # Assert one of the log for JSON format to check correctness
        print("Validate Logs in Sumo Logic.")
        self.sumo_resource.assert_logs()

        if len(self.sumo_resource.verificationErrors) > 0:
            print("Assertions failures are:- %s." % '\n'.join(self.sumo_resource.verificationErrors))
            assert len(self.sumo_resource.verificationErrors) == 0


if __name__ == '__main__':
    unittest.main()
