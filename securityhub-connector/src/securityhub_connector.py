import json
import time
from datetime import datetime
import boto3
import os
import logging
import traceback
import uuid
from src.utils import retry


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_account_id(context):
    account_id = context.invoked_function_arn.split(":")[4]
    account_id = os.getenv("aws_account_id", account_id)
    return account_id


def generate_id(search_name, account_id, region_name):
    uid = uuid.uuid4()
    fid = "sumologicinc:%s:%s:%s/finding/%s" % (region_name, account_id, search_name, uid)
    return fid


def convert_to_utc(timestamp):
    try:
        if not isinstance(timestamp, int):
            ts = timestamp.replace(",", "")
            ts = int(timestamp)
        ts = ts/1000 if len(timestamp) >= 13 else ts  # converting to seconds
        utcdate = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    except Exception as e:
        logger.error("Unable to convert %s Error %s" % (timestamp, e))
        utcdate = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    return utcdate


def generate_findings(data, account_id, region_name):
    #Todo remove externalid, change to security hub, add productarn,update sdk, chunking
    all_findings = []
    for row in data['Rows']:
        row["finding_time"] = convert_to_utc(row["finding_time"])
        finding = {
            "SchemaVersion": "2018-10-08",
            "ProductArn": "arn:aws:securityhub:%s:%s:product/sumologicinc/sumologic-lm" % (region_name, account_id),
            "Description": data.get("Description", ""),
            "SourceUrl": data.get("SourceUrl", ""),
            "GeneratorId": data["GeneratorID"],
            "AwsAccountId": row.get("aws_account_id", account_id),
            "Id": generate_id(data["GeneratorID"], account_id, region_name),
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
    except ValueError:
        return None, "Param Validation Failed: %s" % str(e)
    except KeyError as e:
        return None, str(e)
    else:
        return data, None


@retry(ExceptionToCheck=(Exception,), max_retries=3, multiplier=2, logger=logger)
def insert_findings(findings, region, securityhub_cli=None):
    logger.info("inserting findings %d" % len(findings))
    if not securityhub_cli:
        securityhub_cli = boto3.client('securityhub', region_name=region)
    resp = securityhub_cli.batch_import_findings(
        Findings=findings
    )

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

    logger.info(body)
    return status_code, body


def lambda_handler(event, context):
    account_id = get_account_id(context)
    region_name = os.environ.get("REGION", os.getenv("AWS_REGION"))
    logger.info("Invoking lambda_handler in Region %s of Account %s" % (region_name, account_id))
    # logger.info("event %s" % event)
    data, err = validate_params(event['body'])
    if not err:
        try:
            findings = generate_findings(data, account_id, region_name)
            status_code, body = insert_findings(findings, region_name)
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
