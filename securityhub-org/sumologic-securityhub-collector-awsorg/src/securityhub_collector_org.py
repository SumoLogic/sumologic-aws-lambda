import json
import os
import logging
import sys
import requests
sys.path.insert(0, '/opt')  # layer packages are in opt directory
from collections import defaultdict

SUMO_ENDPOINT = os.getenv("SUMO_ENDPOINT")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
session = requests.Session()
headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

def post_to_sumo(findings, silent=False):

    findings_data = "\n\n".join([json.dumps(data) for data in findings])
    is_success = False
    try:
        logger.info("findings_data: " + json.dumps(findings_data))
        r = session.post(SUMO_ENDPOINT, data=findings_data, headers=headers) 
    except Exception as e:
        logger.error("Failed to post findings to Sumo: %s" % str(e))
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
            post_to_sumo(finding_list)

        logger.info("Finished Sending NumFindings: %d" % (count))


def lambda_handler(event, context):
    logger.info("Invoking SecurityHubCollector source %s region %s" % (event['source'], event['region']))
    findings = event['detail'].get('findings', [])
    send_findings(findings, context)


if __name__ == '__main__':

    event = json.load(open('../test/testevent.json'))
    BUCKET_NAME = "securityhubfindings"

    class context:
        aws_request_id = "testid12323"

    lambda_handler(event, context)
