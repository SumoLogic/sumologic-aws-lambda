import json
from datetime import datetime
import os
import logging
import traceback
import uuid
import sys
sys.path.insert(0, '/opt')
import boto3
from botocore.exceptions import ClientError
from utils import retry


def get_product_arn(securityhub_region):
    PROVIDER_ACCOUNT_ID = "956882708938"
    return "arn:aws:securityhub:%s:%s:product/sumologicinc/sumologic-mda" % (securityhub_region, PROVIDER_ACCOUNT_ID)


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_lambda_account_id(context):
    lambda_account_id = context.invoked_function_arn.split(":")[4]
    return lambda_account_id


def generate_id(search_name, finding_account_id, securityhub_region):
    uid = uuid.uuid4()
    #Todo uuid generated from fields: ResourceID, ResourceType , Severity, Compliance, Type, Title and AWS AccountId
    fid = "sumologic:%s:%s:%s/finding/%s" % (securityhub_region, finding_account_id, search_name, uid)
    return fid


def convert_to_utc(timestamp):
    #Todo change to convert to RFC3339
    try:
        if not isinstance(timestamp, int):
            timestamp = timestamp.replace(",", "")
            ts = int(timestamp)
        else:
            ts = timestamp
            timestamp = str(timestamp)
        ts = ts/1000 if len(timestamp) >= 13 else ts  # converting to seconds
        utcdate = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    except Exception as e:
        logger.error("Unable to convert %s Error %s" % (timestamp, e))
        utcdate = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return utcdate


def generate_findings(data, finding_account_id, securityhub_region):
    #Todo remove externalid, change to security hub, add productarn,update sdk, chunking
    all_findings = []
    product_arn = get_product_arn(securityhub_region)
    for row in data['Rows']:
        row["finding_time"] = convert_to_utc(row["finding_time"])
        finding_account_id = row.get("aws_account_id", finding_account_id)
        finding = {
            "SchemaVersion": "2018-10-08",
            "RecordState": "ACTIVE",
            "ProductArn": product_arn,
            "Description": data.get("Description", ""),
            "SourceUrl": data.get("SourceUrl", ""),
            "GeneratorId": data["GeneratorID"],
            "AwsAccountId": finding_account_id,
            "Id": generate_id(data["GeneratorID"], finding_account_id, securityhub_region),
            "Types": [data["Types"]],
            "CreatedAt": row["finding_time"],
            "UpdatedAt": row["finding_time"],
            "FirstObservedAt": row["finding_time"],
            "Resources": [{
                "Type": row["resource_type"],
                "Id": row["resource_id"]
            }],
            "Severity": {
                "Normalized": int(data["Severity"])
            },
            "Title": row["title"]
        }
        if data.get("ComplianceStatus"):
            finding["Compliance"] = {"Status": data["ComplianceStatus"]}
        all_findings.append(finding)

    return all_findings


def check_required_params(data):
    data_params = set(("GeneratorID", "Types", "Rows", "Severity"))
    row_params = set(("finding_time", "resource_type", "resource_id", "title"))
    missing_fields = data_params - set(data.keys())
    missing_fields = missing_fields | (row_params - set(data['Rows'][0].keys()))
    if missing_fields:
        raise KeyError("%s Fields are missing" % ",".join(missing_fields))
    severity = int(data.get("Severity"))
    if severity > 100 or severity < 0:
        raise ValueError("Severity should be between 0 to 100")
    if data.get("ComplianceStatus") and data["ComplianceStatus"] not in ("PASSED", "WARNING", "FAILED", "NOT_AVAILABLE"):
        raise ValueError("ComplianceStatus should be PASSED/WARNING/FAILED/NOT_AVAILABLE")


def validate_params(data):
    try:
        data = json.loads(data)
        data['Rows'] = json.loads(data.get('Rows', '[{}]'))
        check_required_params(data)
    except ValueError as e:
        return None, "Param Validation Error - %s" % str(e)
    except KeyError as e:
        return None, str(e)
    else:
        return data, None


def subscribe_to_sumo(securityhub_cli, securityhub_region):
    product_arn = get_product_arn(securityhub_region)
    try:
        resp = securityhub_cli.start_product_subscription(ProductArn=product_arn)
        subscription_arn = resp.get("ProductSubscriptionArn")
        status_code = resp['ResponseMetadata']['HTTPStatusCode']
        logger.info("Subscribing to Sumo Logic Product StatusCode: %s ProductSubscriptionArn: %s" % (
            status_code, subscription_arn))
    except ClientError as e:
        status_code = e.response['ResponseMetadata']['HTTPStatusCode']
        raise Exception("Failed to Subscribe to Sumo Logic Product StatusCode: %s Error: %s" % (status_code, str(e)))


def process_response(resp):
    status_code = resp["ResponseMetadata"].get("HTTPStatusCode")
    failed_count = resp.get("FailedCount", 0)
    success_count = resp.get("SuccessCount")
    body = "FailedCount: %d SuccessCount: %d StatusCode: %d " % (
        failed_count, success_count, status_code)

    if failed_count > 0:
        err_msg = set()
        for row in resp["Findings"]:
            err_msg.add(row["ErrorMessage"])
        body += "ErrorMessage: %s" % ",".join(err_msg)
    return status_code, body


@retry(ExceptionToCheck=(Exception,), max_retries=1, multiplier=2, logger=logger)
def insert_findings(findings, securityhub_region):
    logger.info("inserting findings %d" % len(findings))

    securityhub_cli = boto3.client('securityhub', region_name=securityhub_region)
    try:
        resp = securityhub_cli.batch_import_findings(
            Findings=findings
        )
        status_code, body = process_response(resp)
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            body = e.response["Error"]["Message"] + " .Enable Sumo Logic as a Finding Provider"
            logger.error(body)
            # disabling automatic subscription to security hub
            # subscribe_to_sumo(securityhub_cli, securityhub_region)
            # resp = securityhub_cli.batch_import_findings(
            #     Findings=findings
            # )
            # status_code, body = process_response(resp)
        else:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            body = e.response["Error"]["Message"]

    logger.info(body)
    return status_code, body


def lambda_handler(event, context):
    lambda_account_id = get_lambda_account_id(context)
    lambda_region = os.getenv("AWS_REGION")
    logger.info("Invoking lambda_handler in Region %s AccountId %s" % (lambda_region, lambda_account_id))
    finding_account_id = os.getenv("AWS_ACCOUNT_ID", lambda_account_id)
    securityhub_region = os.getenv("REGION", lambda_region)
    # logger.info("event %s" % event)
    data, err = validate_params(event['body'])
    # data, err = validate_params(event)
    if not err:
        try:
            findings = generate_findings(data, finding_account_id, securityhub_region)
            status_code, body = insert_findings(findings, securityhub_region)
        except Exception as e:
            status_code, body = 500, "Error: %s Traceback: %s" % (e, traceback.format_exc())
            logger.error(body)
    else:
        status_code = 400
        body = "Bad Request: %s" % err
    return {
        "statusCode": status_code,
        "body": body
    }
