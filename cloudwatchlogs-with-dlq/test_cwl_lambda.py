import unittest
import boto3
import json
from time import sleep
import os
import sys
import datetime
import uuid

BUCKET_PREFIX = "appdevstore"
VERSION = "v1.3.0"
AWS_PROFILE = "default"

class TestLambda(unittest.TestCase):
    TEMPLATE_KEYS_TO_REMOVE = ['SumoCWProcessDLQScheduleRule',
                               'SumoCWEventsInvokeLambdaPermission']

    REGION_MAPPING = {
        "us-east-1": "appdevstore-<uuid>-us-east-1",
        "us-east-2": "appdevstore-<uuid>-us-east-2",
        "us-west-1": "appdevstore-<uuid>-us-west-1",
        "us-west-2": "appdevstore-<uuid>-us-west-2",
        "ap-south-1": "appdevstore-<uuid>-ap-south-1",
        "ap-northeast-2": "appdevstore-<uuid>-ap-northeast-2",
        "ap-southeast-1": "appdevstore-<uuid>-ap-southeast-1",
        "ap-southeast-2": "appdevstore-<uuid>-ap-southeast-2",
        "ap-northeast-1": "appdevstore-<uuid>-ap-northeast-1",
        "ca-central-1": "appdevstore-<uuid>-ca-central-1",
        "eu-central-1": "appdevstore-<uuid>-eu-central-1",
        "eu-west-1": "appdevstore-<uuid>-eu-west-1",
        "eu-west-2": "appdevstore-<uuid>-eu-west-2",
        "eu-west-3": "appdevstore-<uuid>-eu-west-3",
        "eu-north-1": "appdevstore-<uuid>-eu-north-1s",
        "sa-east-1": "appdevstore-<uuid>-sa-east-1",
        "ap-east-1": "appdevstore-<uuid>-ap-east-1s",
        "af-south-1": "appdevstore-<uuid>-af-south-1s",
        "eu-south-1": "appdevstore-<uuid>-eu-south-1",
        "me-south-1": "appdevstore-<uuid>-me-south-1s",
        "me-central-1": "appdevstore-<uuid>-me-central-1",
        "eu-central-2": "appdevstore-<uuid>-eu-central-2ss",
        "ap-northeast-3": "appdevstore-<uuid>-ap-northeast-3s",
        "ap-southeast-3": "appdevstore-<uuid>-ap-southeast-3"
    }

    def get_bucket_name(self, region):
        return self.REGION_MAPPING[region]

    @staticmethod
    def generate_32bit_uuid():
        return uuid.uuid4().int & 0xFFFFFFFF  # Extract only the last 32 bits

    def bucket_exists(self, s3, bucket_name):
        """Check if an S3 bucket exists."""
        try:
            s3.head_bucket(Bucket=bucket_name)
            return True
        except Exception:
            return False

    def create_bucket(self, region, bucket_name):
        """Create an S3 bucket in the specified region if it does not exist."""
        s3 = boto3.client("s3", region_name=region)

        if not bucket_name:
            print(f"No bucket mapping found for region: {region}")
            return

        if self.bucket_exists(s3, bucket_name):
            print(f"Bucket {bucket_name} already exists in {region}.")
            return

        try:
            if region == "us-east-1":
                response = s3.create_bucket(Bucket=bucket_name)
            else:
                response = s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            print(f"Bucket created: {bucket_name} in {region}", response)
        except Exception as e:
            print(f"Error creating bucket {bucket_name}: {e}")

    def upload_code_in_s3(self, region):
        filename = 'cloudwatchlogs-with-dlq.zip'
        boto3.setup_default_session(profile_name=AWS_PROFILE)
        s3 = boto3.client('s3', region)
        print("Uploading zip file %s in S3 bucket (%s) at region (%s)" % (filename, self.bucket_name, region))
        s3.upload_file(filename, self.bucket_name, f"cloudwatchLogsDLQ/{VERSION}/{filename}")

    def setUp(self):
        self.DLQ_QUEUE_NAME = 'SumoCWDeadLetterQueue'
        self.DLQ_Lambda_FnName = 'SumoCWProcessDLQLambda'

        self.config = {
            'AWS_REGION_NAME': os.environ.get("AWS_DEFAULT_REGION",
                                              "ap-southeast-1")
        }
        self.stack_name = "TestCWLStack-%s" % (
            datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        boto3.setup_default_session(profile_name=AWS_PROFILE)
        self.cf = boto3.client('cloudformation',
                               self.config['AWS_REGION_NAME'])
        self.template_name = 'DLQLambdaCloudFormation.json'
        try:
            self.sumo_endpoint_url = os.environ["SumoEndPointURL"]
        except KeyError:
            raise Exception("SumoEndPointURL environment variables are not set")
        self.template_data = self._parse_template(self.template_name)
        # replacing prod zipfile location to test zipfile location
        bucket_name = self.get_bucket_name(self.config['AWS_REGION_NAME'])
        bucket_uuid = str(self.generate_32bit_uuid())
        self.bucket_name = bucket_name.replace("<uuid>", bucket_uuid)
        # create new bucket
        self.create_bucket(self.config['AWS_REGION_NAME'], self.bucket_name)
        bucket_prefix = bucket_name.split("<uuid>")[0]
        bucket_uuid_prefix = f"{bucket_prefix}{bucket_uuid}"
        self.template_data = self.template_data.replace("appdevzipfiles", bucket_uuid_prefix)
        RUNTIME = "nodejs%s" % os.environ.get("NODE_VERSION", "22.x")
        self.template_data = self.template_data.replace("nodejs22.x", RUNTIME)
        print("self.bucket_name", self.bucket_name)
        print("self.template_data", self.template_data)

    def tearDown(self):
        if self.stack_exists(self.stack_name):
            self.delete_stack()
        self.delete_s3_bucket(self.bucket_name)

    def test_lambda(self):

        self.upload_code_in_s3(self.config['AWS_REGION_NAME'])
        self.create_stack()
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.insert_mock_logs_in_DLQ()
        self.assertTrue(int(self.initial_log_count) == 50)
        self.invoke_lambda()
        self.check_consumed_messages_count()

    def delete_s3_bucket(self, bucket_name):
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket_name)

        # Delete all objects
        bucket.objects.all().delete()

        # Delete all object versions (if versioning is enabled)
        bucket.object_versions.all().delete()

        # Delete the bucket
        bucket.delete()
        print(f"Bucket '{bucket_name}' and all objects deleted successfully.")

    def stack_exists(self, stack_name):
        stacks = self.cf.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if self.stack_id_suffix == stack['StackId'].split("/")[2] and stack['StackStatus'] == 'CREATE_COMPLETE':
                print("%s stack exists" % stack_name)
                return True
        return False

    def set_stack_id(self, stack_result):
        self.stack_id_suffix = stack_result['StackId'].split("/")[2]
        self.DLQ_QUEUE_NAME = "%s-%s" % (self.DLQ_QUEUE_NAME, self.stack_id_suffix)
        self.DLQ_Lambda_FnName = "%s-%s" % (self.DLQ_Lambda_FnName,
                                            self.stack_id_suffix)

    def create_stack(self):
        params = {
            'StackName': self.stack_name,
            'TemplateBody': self.template_data,
            'Capabilities': ['CAPABILITY_IAM']
        }
        stack_result = self.cf.create_stack(**params)
        self.set_stack_id(stack_result)
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

    def _get_dlq_url(self):
        if not hasattr(self, 'dlq_queue_url'):
            sqs = boto3.resource('sqs', self.config['AWS_REGION_NAME'])
            queue_name = self._get_queue_name(sqs, self.DLQ_QUEUE_NAME)
            queue = sqs.get_queue_by_name(QueueName=queue_name)
            self.dlq_queue_url = queue.url

        return self.dlq_queue_url

    def insert_mock_logs_in_DLQ(self):
        print("Inserting fake logs in DLQ")
        dlq_queue_url = self._get_dlq_url()
        sqs_client = boto3.client('sqs', self.config['AWS_REGION_NAME'])
        with open('cwlfixtures.json', 'r', encoding='UTF-8') as file:
            mock_logs = json.load(file)
        for log in mock_logs:
            sqs_client.send_message(QueueUrl=dlq_queue_url,
                                    MessageBody=json.dumps(log))
        sleep(60)  # waiting for messages to be ingested in SQS
        self.initial_log_count = self._get_message_count()
        print("Inserted %s Messages in %s" % (
            self.initial_log_count, dlq_queue_url))

    def _get_message_count(self):
        sqs = boto3.resource('sqs', self.config['AWS_REGION_NAME'])
        queue_name = self._get_queue_name(sqs, self.DLQ_QUEUE_NAME)
        queue = sqs.get_queue_by_name(QueueName=queue_name)
        return int(queue.attributes.get('ApproximateNumberOfMessages'))

    def _get_queue_name(self, sqs_client, pattern):
        import re
        for queue in sqs_client.queues.all():
            queue_name = queue.attributes['QueueArn'].split(':')[-1]
            if re.search(pattern, queue_name):
                print("QueueName: %s" % queue_name)
                return queue_name
        return ''

    def _get_dlq_function_name(self, lambda_client, pattern):
        import re
        for func in lambda_client.list_functions()['Functions']:
            if re.search(pattern, func['FunctionName']):
                print("FunctionName: %s" % func['FunctionName'])
                return func['FunctionName']
        return ''

    def invoke_lambda(self):
        lambda_client = boto3.client('lambda', self.config['AWS_REGION_NAME'])
        lambda_func_name = self._get_dlq_function_name(lambda_client,
                                                       self.DLQ_Lambda_FnName)
        response = lambda_client.invoke(FunctionName=lambda_func_name)
        print("Invoking lambda function", response)

    def check_consumed_messages_count(self):
        sleep(30)
        final_message_count = self._get_message_count()
        print("Testing number of consumed messages initial: %s final: %s processed: %s" % (
            self.initial_log_count, final_message_count,
            self.initial_log_count - final_message_count))
        self.assertEqual(self.initial_log_count, final_message_count)

    def _parse_template(self, template):
        with open(template) as template_fileobj:
            template_data = template_fileobj.read()
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        #removing schedule rule to prevent lambda being triggered while testing
        #becoz we are invoking lambda directly
        template_data = eval(template_data)
        template_data["Parameters"]["SumoEndPointURL"]["Default"] = self.sumo_endpoint_url
        for key in self.TEMPLATE_KEYS_TO_REMOVE:
            template_data["Resources"].pop(key)
        template_data = str(template_data)
        return template_data



if __name__ == '__main__':
    unittest.main()
