import time
from functools import wraps


def fixed_sleep(fixed_wait_time):
    def handler():
        return fixed_wait_time
    return handler


def incrementing_sleep(wait_time_inc, start_wait_time=3):
    attempt = 1

    def handler():
        nonlocal attempt
        print("generating time", attempt)
        result = start_wait_time + (attempt-1)*wait_time_inc
        attempt += 1
        return result
    return handler


def exponential_sleep(multiplier):
    attempt = 1

    def handler():
        nonlocal attempt
        exp = 2 ** attempt
        result = multiplier * exp
        attempt += 1
        return result
    return handler


def retry_if_exception_of_type(retryable_types):
    def _retry_if_exception_these_types(exception):
        return isinstance(exception, retryable_types)
    return _retry_if_exception_these_types


def retry(ExceptionToCheck=(Exception,), max_retries=4,
          logger=None, handler_type=exponential_sleep, *hdlrargs, **hdlrkwargs):

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            delay_handler = handler_type(*hdlrargs, **hdlrkwargs)
            retries_left, wait_time = max_retries, delay_handler()
            while retries_left > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), wait_time)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(wait_time)
                    retries_left -= 1
                    wait_time = delay_handler()
            return f(*args, **kwargs)

        return f_retry

    return deco_retry
