import unittest
import boto3
import json
from time import sleep


class TestLambda(unittest.TestCase):

    def setUp(self):
        self.config = {
            'AWS_REGION_NAME': 'us-east-2'
        }
        # aws_access_key_id aws_secret_access_key
        self.stack_name = "TestCWLStack"
        self.cf = boto3.client('cloudformation',
                               self.config['AWS_REGION_NAME'])
        self.template_name = 'DLQLambdaCloudFormation.json'
        self.template_data = self._parse_template(self.template_name)

    def tearDown(self):
        if self.stack_exists(self.stack_name):
            self.delete_stack()

    def test_lambda(self):
        self.upload_code_in_S3()
        self.create_stack()
        print("Testing Stack Creation")
        self.assertTrue(self.stack_exists(self.stack_name))
        self.insert_mock_logs_in_DLQ()
        self.assertTrue(int(self._get_message_count()) == 50)
        self.invoke_lambda()
        self.check_consumed_messages_count()

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

    def _get_dlq_url(self):
        if (not hasattr(self, 'dlq_queue_url')):
            sqs = boto3.resource('sqs', self.config['AWS_REGION_NAME'])
            queue = sqs.get_queue_by_name(QueueName='LambdaDLQ')
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

        self.initial_log_count = self._get_message_count()
        print("Inserted %s Messages in %s" % (
            self.initial_log_count, dlq_queue_url))

    def _get_message_count(self):
        sqs = boto3.resource('sqs', self.config['AWS_REGION_NAME'])
        queue = sqs.get_queue_by_name(QueueName='LambdaDLQ')
        return queue.attributes.get('ApproximateNumberOfMessages')

    def _get_dlq_function_name(self, lambda_client, pattern):
        import re
        for func in lambda_client.list_functions()['Functions']:
            if re.search(pattern, func['FunctionName']):
                return func['FunctionName']
        return ''

    def invoke_lambda(self):
        lambda_client = boto3.client('lambda', self.config['AWS_REGION_NAME'])
        lambda_func_name = self._get_dlq_function_name(lambda_client,
                                                       r'DLQProcessorLambda')
        response = lambda_client.invoke(FunctionName=lambda_func_name)
        print("Invoking lambda function", response)

    def check_consumed_messages_count(self):
        sleep(120)
        final_message_count = self._get_message_count()
        print("Testing number of consumed messages initial: %s final: %s processed: %s" % (
            self.initial_log_count, final_message_count,
            int(self.initial_log_count) - int(final_message_count)))
        self.assertGreater(self.initial_log_count, final_message_count)

    def _parse_template(self, template):
        with open(template) as template_fileobj:
            template_data = template_fileobj.read()
        print("Validating cloudformation template")
        self.cf.validate_template(TemplateBody=template_data)
        #removing schedulerule to prevent lambda being triggered while testing
        #becoz we are invoking lambda directly
        template_data = eval(template_data)
        template_data["Resources"].pop("ScheduleRule")
        template_data["Resources"].pop("PermissionForEventsToInvokeLambda")
        template_data = str(template_data)

        return template_data

    def upload_code_in_S3(self):
        print("Uploading zip file in S3")
        s3 = boto3.client('s3', self.config['AWS_REGION_NAME'])
        filename = 'dlqprocessor.zip'
        bucket_name = 'appdevfiles'
        s3.upload_file(filename, bucket_name, filename)


if __name__ == '__main__':
    unittest.main()
