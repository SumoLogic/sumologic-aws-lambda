import unittest
import boto3
import json
from time import sleep
import os
import sys
import datetime

BUCKET_PREFIX = "appdevstore"


class TestLambda(unittest.TestCase):
    TEMPLATE_KEYS_TO_REMOVE = ['SumoCWProcessDLQScheduleRule',
                               'SumoCWEventsInvokeLambdaPermission']

    def setUp(self):
        self.DLQ_QUEUE_NAME = 'SumoCWDeadLetterQueue'
        self.DLQ_Lambda_FnName = 'SumoCWProcessDLQLambda'

        self.config = {
            'AWS_REGION_NAME': os.environ.get("AWS_DEFAULT_REGION",
                                              "us-east-2")
        }
        self.stack_name = "TestCWLStack-%s" % (
            datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"))
        self.cf = boto3.client('cloudformation',
                               self.config['AWS_REGION_NAME'])
        self.template_name = 'DLQLambdaCloudFormation.json'
        try:
            self.sumo_endpoint_url = os.environ["SumoEndPointURL"]
        except KeyError:
            raise Exception("SumoEndPointURL environment variables are not set")
        self.template_data = self._parse_template(self.template_name)
        # replacing prod zipfile location to test zipfile location
        self.template_data = self.template_data.replace("appdevzipfiles", BUCKET_PREFIX)
        RUNTIME = "nodejs%s" % os.environ.get("NODE_VERSION", "10.x")
        self.template_data = self.template_data.replace("nodejs10.x", RUNTIME)

    def tearDown(self):
        if self.stack_exists(self.stack_name):
            self.delete_stack()

    def test_lambda(self):

        upload_code_in_S3(self.config['AWS_REGION_NAME'])
        self.create_stack()
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.insert_mock_logs_in_DLQ()
        self.assertTrue(int(self.initial_log_count) == 50)
        self.invoke_lambda()
        self.check_consumed_messages_count()

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
        if (not hasattr(self, 'dlq_queue_url')):
            sqs = boto3.resource('sqs', self.config['AWS_REGION_NAME'])
            queue_name = self._get_queue_name(sqs, self.DLQ_QUEUE_NAME)
            queue = sqs.get_queue_by_name(QueueName=queue_name)
            self.dlq_queue_url = queue.url

        return self.dlq_queue_url

    def insert_mock_logs_in_DLQ(self):
        print("Inserting fake logs in DLQ")
        dlq_queue_url = self._get_dlq_url()
        sqs_client = boto3.client('sqs', self.config['AWS_REGION_NAME'])
        mock_logs = json.load(open('cwlfixtures.json'))
        for log in mock_logs:
            sqs_client.send_message(QueueUrl=dlq_queue_url,
                                    MessageBody=json.dumps(log))
        sleep(15)  # waiting for messages to be ingested in SQS
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
        self.assertGreater(self.initial_log_count, final_message_count)

    def _parse_template(self, template):
        with open(template) as template_fileobj:
            template_data = template_fileobj.read()
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        #removing schedulerule to prevent lambda being triggered while testing
        #becoz we are invoking lambda directly
        template_data = eval(template_data)
        template_data["Parameters"]["SumoEndPointURL"]["Default"] = self.sumo_endpoint_url
        for key in self.TEMPLATE_KEYS_TO_REMOVE:
            template_data["Resources"].pop(key)
        template_data = str(template_data)
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
    filename = 'cloudwatchlogs-with-dlq.zip'
    print("Uploading zip file %s in S3 %s" % (filename, region))
    s3 = boto3.client('s3', region)
    bucket_name = get_bucket_name(region)
    s3.upload_file(filename, bucket_name, filename,
                   ExtraArgs={'ACL': 'public-read'})


def generate_fixtures(region, count):
    data = []
    sqs = boto3.client('sqs', region)
    for x in range(0, count, 10):
        response = sqs.receive_message(
            QueueUrl='https://sqs.us-east-2.amazonaws.com/456227676011/SumoCWDeadLetterQueue',
            MaxNumberOfMessages=10,
        )
        for msg in response['Messages']:
            data.append(eval(msg['Body']))

    return data[:count]


def prod_deploy():
    global BUCKET_PREFIX
    BUCKET_PREFIX = 'appdevzipfiles'
    upload_code_in_multiple_regions()
    print("Uploading template file in S3")
    s3 = boto3.client('s3', "us-east-1")
    filename = 'DLQLambdaCloudFormation.json'
    bucket_name = "appdev-cloudformation-templates"
    s3.upload_file(filename, bucket_name, filename,
                   ExtraArgs={'ACL': 'public-read'})
    print("Deployment Successfull: ALL files copied to Sumocontent")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        BUCKET_PREFIX = sys.argv.pop()

    unittest.main()
