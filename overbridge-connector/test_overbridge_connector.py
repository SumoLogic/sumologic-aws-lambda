import unittest
from overbridge_connector import lambda_handler
from utils import retry, incrementing_sleep, fixed_sleep
import copy


class TestLambda(unittest.TestCase):

    def setUp(self):
        class Event:
            with open("fixtures.json") as f:
                body = f.read()

        class Context:
            invoked_function_arn="arn:aws:lambda:us-east-1:956882708938:function:OverbridgeLambda"

        self.context = Context()
        self.event = Event()

    def tearDown(self):
        pass

    def test_send_success(self):
        result = lambda_handler(self.event, self.context)
        print(result)

    def test_send_failure(self):
        event = copy.copy(self.event)
        event.body.replace("InsertFindingsScheduledSearch", "1")
        result = lambda_handler(self.event, self.context)
        print(result)

    def test_validation(self):
        event = copy.copy(self.event)
        event.body.replace('\"Types\": \"Security\",', "")
        result = lambda_handler(self.event, self.context)
        print(result)

    def test_retry(self):
        class Logger:
            def __init__(self):
                self.messages = []

            def warning(self, msg):
                self.messages.append(msg)
        logger = Logger()
        @retry(ExceptionToCheck=(KeyError,), max_retries=3, logger=logger, handler_type=fixed_sleep, fixed_wait_time=2)
        def func():
            data = {}
            return data["key"]
        with self.assertRaises(Exception) as context:
            func()

        print(logger.messages)

        logger = Logger()
        @retry(ExceptionToCheck=(ValueError,), max_retries=2, logger=logger, handler_type=incrementing_sleep, wait_time_inc=2)
        def func():
            data = {}
            return data["key"]

        with self.assertRaises(Exception) as context:
            func()
        print(logger.messages)

if __name__ == '__main__':
    unittest.main()
