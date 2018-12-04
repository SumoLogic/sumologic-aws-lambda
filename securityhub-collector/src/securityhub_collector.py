import json
import boto3
import os
import logging
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime, timezone
import dateutil.parser


MAX_RESULTS = 10
LAMBDA_TRIGGER_TIME_OFFSET = 30000
BUCKET_NAME = os.getenv("S3_LOG_BUCKET")


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_filtered_findings(securityhub_cli, filters, next_token=None, max_results=MAX_RESULTS):
    params = {
        "Filters": filters,
        "MaxResults": max_results
    }
    findings = []
    if next_token:
        params["NextToken"] = next_token

    try:
        resp = securityhub_cli.get_findings(**params)
    except Exception as e:
        logger.error("Error in Getting Findings %s" % str(e))
        return [], None
    else:
        if resp["ResponseMetadata"].get("HTTPStatusCode") != 200:
            logger.error("Error in Getting Findings %s" % resp)
            return [], None
        else:
            next_token = resp.get('NextToken')
            logger.info("Findings fetched: %d  Metadata: %s NextToken: %s" % (
                len(resp["Findings"]), resp["ResponseMetadata"], next_token))
            findings = resp["Findings"]
            return findings, next_token


def post_to_s3(findings, filename):
    #Todo buffering logic https://github.com/SumoLogic/sumologic-collectd-plugin/blob/master/sumologic_collectd_metrics/metrics_batcher.py
    lambda_region = os.getenv("AWS_REGION")
    findings_data = "\n\n".join([json.dumps(data) for data in findings])
    is_success = False
    s3cli = boto3.client('s3', region_name=lambda_region)
    try:
        response = s3cli.put_object(Body=findings_data, Bucket=BUCKET_NAME, Key=filename)
        is_success = True
        logger.info("Saved %d findings to s3 %s status_code: %s" % (len(findings), filename, response["ResponseMetadata"].get("HTTPStatusCode")))
    except Exception as e:
        logger.error("Failed to post findings to S3: %s" % str(e))

    return is_success


def acquire_lock_on_fp(dynamodbcli, product_arn, lock_table_name):
    # acquiring lock only if lock is not there
    table = dynamodbcli.Table(lock_table_name)
    try:
        response = table.update_item(
            Key={
                'product_arn': product_arn
            },
            ReturnValues='UPDATED_NEW',
            ReturnConsumedCapacity='TOTAL',
            ReturnItemCollectionMetrics='NONE',
            UpdateExpression='set is_locked = :val1, last_locked_date = :val3',
            ConditionExpression='is_locked = :val2',
            ExpressionAttributeValues={
                ':val1': Decimal('1'),
                ':val2': Decimal('0'),
                ':val3': get_current_datetime().isoformat()
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            logger.warning("Failed to acquire lock Provider: %s Message: %s" % (product_arn, e.response['Error']['Message']))
        else:
            logger.error("Error in Acquiring lock %s" % str(e))
        return False
    else:
        logger.info("Lock acquired Provider: %s Message: %s" % (product_arn, response["Attributes"]))
        return True


def get_current_datetime():
    return datetime.now(tz=timezone.utc)


def get_datetime_from_isoformat(date_str):
    return dateutil.parser.parse(date_str)


def convert_to_utc_isoformat(isofmt_date_str):
    date_obj = get_datetime_from_isoformat(isofmt_date_str)
    utc_date_obj = date_obj.astimezone(timezone.utc)
    return utc_date_obj.isoformat()


def release_lock_on_fp(dynamodbcli, product_arn, last_event_date, lock_table_name):
    # releasing lock and updating last_event_date
    last_event_date = convert_to_utc_isoformat(last_event_date)
    table = dynamodbcli.Table(lock_table_name)
    try:
        response = table.update_item(
            Key={
                'product_arn': product_arn
            },
            ReturnValues='UPDATED_NEW',
            ReturnConsumedCapacity='TOTAL',
            ReturnItemCollectionMetrics='NONE',
            UpdateExpression='set is_locked = :val1, last_event_date = :val3',
            ConditionExpression='is_locked = :val2',
            ExpressionAttributeValues={
                ':val1': Decimal(0),
                ':val2': Decimal(1),
                ':val3': last_event_date
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            logger.warning("Failed to release lock Provider: %s Message: %s" % (product_arn, e.response['Error']['Message']))
        else:
            logger.error("Error in Releasing lock %s" % str(e))
        return False
    else:
        logger.info("Lock released Provider: %s Message: %s" % (product_arn, response["Attributes"]))
        return True


def invoke_lambda(function_name, start_date, last_date, last_event_date, product_arn, next_token):
    region = os.getenv("AWS_REGION")
    lambda_cli = boto3.client('lambda', region_name=region)
    payload = bytes(json.dumps({
        "product_arn": product_arn,
        "start_date": start_date,
        "last_date": last_date,
        "last_event_date": last_event_date,
        "next_token": next_token
    }), "utf-8")
    try:
        resp = lambda_cli.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=payload
        )
        logger.info("Self Invocation Response: %s" % resp["ResponseMetadata"])
    except Exception as e:
        logger.error("Failed to Invoke Lambda Error: %s" % (e))


def is_self_invocation_required(context, start_date, last_date, last_event_date, product_arn, next_token):
    time_till_timeout = context.get_remaining_time_in_millis()
    next_request = True if next_token else False  # fetching next batch of findings if next token present in current invocation
    logger.info("checking time_till_timeout: %s" % time_till_timeout)
    if time_till_timeout <= LAMBDA_TRIGGER_TIME_OFFSET and next_request:
        next_request = False
        logger.info("Self Invocation with %s %s %s %s" % (next_token, start_date, last_date, product_arn))
        invoke_lambda(context.function_name, start_date, last_date, last_event_date, product_arn, next_token)

    return next_request


def send_findings(context, start_date, last_date, last_event_date, product_arn, next_token):
    lambda_region = os.getenv("AWS_REGION")
    securityhub_region = os.getenv("REGION", lambda_region)
    securityhub_cli = boto3.client('securityhub', region_name=securityhub_region)
    filters = {
        "ProductArn": [{
            "Value": product_arn,
            "Comparison": "EQUALS"
        }],
        "UpdatedAt": [{
            "Start": start_date,
            "End": last_date
        }],
        "RecordState": [{
            "Value": "ACTIVE",
            "Comparison": "EQUALS"
        }]
    }
    next_request = True
    count = 0
    while next_request:
        count += 1
        findings, next_token = get_filtered_findings(securityhub_cli, filters, next_token)
        if len(findings) > 0:
            new_last_event_date = max(findings, key=lambda x: x["UpdatedAt"])["UpdatedAt"]
            filename = "%s-%s-%d-%s" % (product_arn, new_last_event_date, count, context.aws_request_id)
            is_success = post_to_s3(findings, filename)
            if not is_success:
                return last_event_date  # if s3 fails then release lock and update last_event date to last successfully sent date
            else:
                last_event_date = max(last_event_date, new_last_event_date)
        next_request = is_self_invocation_required(context, start_date, last_date, last_event_date, product_arn, next_token)
        logger.info("Finished Fetching Page: %d NumFindings: %d Next_Request: %s Last_Event_Date: %s" % (count, len(findings), next_request, last_event_date))

    return last_event_date


def lambda_handler(event, context):
    product_arn = event["product_arn"]
    logger.info("Invoking SecurityHubCollector for arn: %s event: %s" % (product_arn, event))
    start_date = event["start_date"]
    last_date = event["last_date"]
    # passing last event date because if somehow get_filtered_findings returns empty then we can update table to previous invocation's last event date
    last_event_date = event["last_event_date"]
    next_token = event.get("next_token")
    lambda_region = os.getenv("AWS_REGION")
    # dynamodbcli = boto3.resource('dynamodb', region_name=lambda_region, endpoint_url="http://localhost:8000")
    dynamodbcli = boto3.resource('dynamodb', region_name=lambda_region)
    lock_table_name = os.getenv("LOCK_TABLE")
    lock_acquired = acquire_lock_on_fp(dynamodbcli, product_arn, lock_table_name)
    if lock_acquired:
        try:
            last_event_date = send_findings(context, start_date, last_date, last_event_date, product_arn, next_token)
        except Exception as e:
            logger.error("Error in send_finding: %s" % str(e))
        finally:
            release_lock_on_fp(dynamodbcli, product_arn, last_event_date, lock_table_name)


if __name__ == '__main__':
    event = {
        "product_arn": "arn:aws:securityhub:us-east-1::product/aws/inspector",
        "start_date": "1970-01-01T00:00:00+00:00",
        "last_date": "2018-11-29T00:00:00+00:00"
    }
    os.environ["S3_LOG_BUCKET"] = "securityhubfindings"
    lambda_handler(event, None)
