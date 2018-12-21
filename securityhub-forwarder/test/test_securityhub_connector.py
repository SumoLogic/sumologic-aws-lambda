import unittest
import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from utils import retry, incrementing_sleep, fixed_sleep
from securityhub_forwarder import lambda_handler

del sys.path[0]


class TestLambda(unittest.TestCase):

    def setUp(self):
        #Todo:  enable sec hub
        self.event = {}
        with open("fixtures.json") as f:
            self.event['body'] = f.read()
        os.environ["AWS_REGION"] = "us-east-1"
        class Context:
            invoked_function_arn="arn:aws:lambda:us-east-1:956882708938:function:OverbridgeLambda"

        self.context = Context()

    def tearDown(self):
        pass

    def test_send_success(self):
        result = lambda_handler(self.event, self.context)
        self.assertEqual(result['statusCode'], 200)
        self.assertTrue(result['body'] == 'FailedCount: 0 SuccessCount: 3 StatusCode: 200 ', "%s body is not matching" % result['body'])

    def test_send_failure(self):
        event = copy.copy(self.event)
        event['body'] = event['body'].replace('\"Severity\": 30', '\"Severity\":200')
        result = lambda_handler(event, self.context)
        self.assertEqual(result['statusCode'], 400)
        self.assertTrue(result['body'] == 'Bad Request: Param Validation Error - Severity should be between 0 to 100', "%s body is not matching" % result['body'])

    def test_compliance_status_failure(self):
        pass

    def test_different_account_id(self):
        event = copy.copy(self.event)
        # os.environ["AWS_REGION"] = "us-east-1"
        # os.environ["AWS_ACCOUNT_ID"] = "456227676011"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_ACCOUNT_ID"] = "068873283051"
        result = lambda_handler(event, self.context)
        self.assertEqual(result['statusCode'], 200)
        self.assertTrue(result['body'] == 'FailedCount: 0 SuccessCount: 3 StatusCode: 200 ', "%s body is not matching" % result['body'])

    def test_different_region(self):
        pass

    def test_validation(self):
        event = copy.copy(self.event)
        event['body'] = event['body'].replace('\"Types\": \"Software and Configuration Checks/Industry and Regulatory Standards/HIPAA Controls\",', "")
        result = lambda_handler(event, self.context)
        self.assertEqual(result['statusCode'], 400)
        self.assertTrue(result['body'] == "Bad Request: 'Types Fields are missing'", "%s body is not matching" % result['body'])

    def test_retry(self):
        class Logger:
            def __init__(self):
                self.messages = []

            def warning(self, msg):
                self.messages.append(msg)
        logger1 = Logger()
        @retry(ExceptionToCheck=(KeyError,), max_retries=3, logger=logger1, handler_type=fixed_sleep, fixed_wait_time=2)
        def func():
            data = {}
            return data["key"]
        with self.assertRaises(Exception) as context:
            func()

        self.assertTrue(len(logger1.messages) == 2, "fixed_sleep(2) with 3 retries should contain 2 messages")

        logger2 = Logger()
        @retry(ExceptionToCheck=(ValueError,), max_retries=2, logger=logger2, handler_type=incrementing_sleep, wait_time_inc=2)
        def func():
            data = {}
            return data["key"]

        with self.assertRaises(Exception) as context:
            func()
        self.assertTrue(len(logger2.messages) == 0, "incremental_sleep(2) with 2 retries but with ValueError(retry not allowed)")


        logger3 = Logger()
        @retry(ExceptionToCheck=(KeyError,), max_retries=2, logger=logger3, handler_type=incrementing_sleep, wait_time_inc=2)
        def func():
            data = {}
            return data["key"]

        with self.assertRaises(Exception) as context:
            func()
        self.assertTrue(len(logger3.messages) == 1, "incremental_sleep(2) with 2 retries should contain 1 message")

if __name__ == '__main__':

    unittest.main()
