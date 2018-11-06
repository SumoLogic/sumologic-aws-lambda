import json
import boto3
import os
import logging
import traceback
import uuid
from datetime import datetime
# from src.utils import retry


MAX_RESULTS = 10
SECONDS_REMAINING_BEFORE_INVOCATION=30000
BUCKET_NAME = os.getenv("S3_LOG_BUCKET", "sumo_findings_bucket-%d" % uuid.uuid4())


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_filtered_findings(securityhub_cli, filters, next_token=None, max_results=MAX_RESULTS):
    #Todo what happens if it throws error
    params = {
        "Filters": filters,
        "MaxResults": max_results
    }
    findings = []
    if next_token:
        params["NextToken"] = next_token
    resp = securityhub_cli.get_findings(**params)
    next_token = resp.get('NextToken')
    if resp["ResponseMetadata"].get("HTTPStatusCode") != 200:
        logger.error("Error in Fetching Findings %s" % resp)
    else:
        logger.info("Findings fetched: %d  Metadata: %s NextToken: %s" % (
            len(resp["Findings"]), resp["ResponseMetadata"], next_token))
        findings = resp["Findings"]
    return findings, next_token


def post_to_s3(findings, filename):
    #Todo buffering logic https://github.com/SumoLogic/sumologic-collectd-plugin/blob/master/sumologic_collectd_metrics/metrics_batcher.py
    #Todo what happens if it throws error
    logger.info("saving %d findings to s3 %s" % (len(findings), filename))
    findings_data = "\n\n".join([json.dumps(data) for data in findings])
    s3cli = boto3.client('s3', region_name=os.getenv("AWS_REGION"))
    s3cli.put_object(Body=findings_data, Bucket=BUCKET_NAME, Key=filename)


def release_lock():
    #Todo update date with last event date
    pass


def invoke_lambda():
    # Todo common logic from scheduler
    pass


def is_self_invocation_required(context, next_token, start_date, last_date, product_arn):
    time_till_timeout = context.get_remaining_time_in_millis()
    if time_till_timeout <= 30000:
        logger.info("self invoking with %s %s %s %s time_till_timeout: %s" % (next_token, start_date, last_date, product_arn, time_till_timeout))
        invoke_lambda()
        next_request = release_lock = False
    else:
        next_request = next_token is not None
        release_lock = True
    return next_request, release_lock


def send_findings(context, start_date, last_date, product_arn, next_token):

    securityhub_cli = boto3.client('securityhub', region_name=os.getenv("AWS_REGION"))

    filters = {
        "ProductArn": [{
            "Value": product_arn,
            "Comparison": "EQUALS"
        }],
        "CreatedAt": [{
            "Start": start_date,
            "End": last_date
        }]
    }
    next_request = release_lock = True
    count = 0
    while next_request:
        count += 1
        findings, next_token = get_filtered_findings(securityhub_cli, filters, next_token)
        if len(findings) > 0:
            filename = "%s-%s-%s" % (product_arn, start_date, last_date)
            post_to_s3(findings, filename)
        next_request, release_lock = is_self_invocation_required(context, next_token, start_date, last_date, product_arn)
        logger.info("Finished Fetching Page: %d for ProductArn: %s Next_Request: %s Release_Lock: %s" % (
            count, product_arn, next_request, release_lock))

    if release_lock:
        logger.info("releasing lock")
        #Todo update lock if lock is old
        release_lock()


def lambda_handler(event, context):
    logger.info("Invoking SecurityHubProcessor")
    print(event)
    product_arn = event["product_arn"]
    start_date = datetime.fromtimestamp(0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    last_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    next_token = event.get("next_token")
    send_findings(context, start_date, last_date, product_arn, next_token)
