import json
# import time
import boto3
import os
import logging
import traceback
# from src.utils import retry
from concurrent import futures


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_active_product_vendors():
    #Todo change when api is available or update lock + (remove old vendors)
    product_arns = []
    region = os.getenv("AWS_REGION")
    securityhub_cli = boto3.client('securityhub', region_name=region)
    resp = securityhub_cli.get_findings_statistics(
        Aggregations=[{"AggregationField": "ProductArn"}]
    )
    aggdata = resp["Aggregations"]
    if len(aggdata) > 0:
        product_arns = [row['Bucket'] for row in aggdata[0]["AggregationValues"]]
    return product_arns


def invoke_lambda(product_arn):
    region = os.getenv("AWS_REGION")
    lambda_cli = boto3.client('lambda', region_name=region)
    payload = bytes(json.dumps({"product_arn": product_arn}), "utf-8")
    response = lambda_cli.invoke(
        FunctionName='SecurityHubProcessor',
        InvocationType='Event',
        Payload=payload
    )
    return response


def trigger_lambdas(product_arns):
    logger.info("Triggering lambdas for %d product_arns" % len(product_arns))
    with futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_arn = {executor.submit(invoke_lambda, arn): arn for arn in product_arns}
        for future in futures.as_completed(future_to_arn):
            arn = future_to_arn[future]
            try:
                response = future.result()
            except Exception as exc:
                logger.error('%r lambda generated an exception: %s' % (arn, exc))
            else:
                logger.info('%r lambda is scheduled %s' % (arn, response))


def lambda_handler(event, context):
    logger.info("Invoking SecurityHubScheduler")
    product_arns = get_active_product_vendors()
    if len(product_arns) > 0:
        trigger_lambdas(product_arns)
    else:
        logger.info("No ProductArn Found")

if __name__ == '__main__':
    lambda_handler(None, None)
