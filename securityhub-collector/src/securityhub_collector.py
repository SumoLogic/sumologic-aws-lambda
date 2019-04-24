import json
import os
import logging
import sys
sys.path.insert(0, '/opt')  # layer packages are in opt directory
import boto3
from collections import defaultdict


BUCKET_NAME = os.getenv("S3_LOG_BUCKET")
BUCKET_REGION = os.getenv("AWS_REGION")
s3cli = boto3.client('s3', region_name=BUCKET_REGION)


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def post_to_s3(findings, filename, silent=False):

    findings_data = "\n\n".join([json.dumps(data) for data in findings])
    is_success = False
    try:
        response = s3cli.put_object(Body=findings_data, Bucket=BUCKET_NAME, Key=filename)
        is_success = True
        logger.info("Saved %d findings to s3 %s status_code: %s" % (len(findings), filename, response["ResponseMetadata"].get("HTTPStatusCode")))
    except Exception as e:
        logger.error("Failed to post findings to S3: %s" % str(e))
        if not silent:
            raise e

    return is_success


def send_findings(findings, context):

    count = 0
    if len(findings) > 0:
        finding_buckets = defaultdict(list)
        for f in findings:
            finding_buckets[f['ProductArn']].append(f)
            count += 1

        for product_arn, finding_list in finding_buckets.items():
            filename = "%s-%s" % (product_arn, context.aws_request_id)
            post_to_s3(finding_list, filename)

        logger.info("Finished Sending NumFindings: %d" % (count))


def lambda_handler(event, context):
    logger.info("Invoking SecurityHubCollector source %s region %s" % (event['source'], event['region']))
    findings = event['detail'].get('findings', [])
    send_findings(findings, context)


if __name__ == '__main__':

    event = json.load(open('../sam/event.json'))
    BUCKET_NAME = "securityhubfindings"

    class context:
        aws_request_id = "testid12323"

    lambda_handler(event, context)
