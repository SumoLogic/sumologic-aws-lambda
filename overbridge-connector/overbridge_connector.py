import json
import time
import boto3
import os
import logging
import traceback
import uuid
from utils import retry


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
    fid = "%s/%s/%s/%s" % (account_id, region_name, search_name, uid)
    return fid


def generate_findings(data, account_id, region_name):
    all_findings = []
    for row in data['Rows']:
        finding = {
            "SchemaVersion": "2018-10-08",
            "ProductArn": "arn:aws:overbridge:%s:%s:provider:private/default" % (region_name, account_id),
            "ExternalId": "8576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f35",
            "Description": data.get("Description", ""),
            "SourceUrl": data.get("SourceUrl", ""),
            "GeneratorId": data["GeneratorID"],
            "AwsAccountId": row.get("aws_account_id", account_id),
            "Id": generate_id(data["GeneratorID"], account_id, region_name),
            "Types": [ "SumoLogic/Compliance" if data['Types'] == "Compliance" else "SumoLogic/Security"],
            "CreatedAt": row["finding_time"], # why not pick up _message_time
            "UpdatedAt": row["finding_time"],
            "FirstObservedAt": row["finding_time"], # why not firetime
            "Resources": [{
                "Type": row["resource_type"],
                "Id": row["resource_id"]
            }],
            "Severity": {
                "Product": float(row.get("severity_product")),
                "Normalized": int(row.get("severity_normalized"))
            }
        }
        all_findings.append(finding)

    return all_findings


def check_required_params(data):
    data_params = set(("GeneratorID", "Types", "Rows"))
    row_params = set(("finding_time", "resource_type", "resource_id", "severity_product", "severity_normalized"))
    missing_fields = data_params - set(data.keys())
    missing_fields = missing_fields | (row_params - set(data['Rows'][0].keys()))
    if missing_fields:
        raise KeyError("%s Fields are missing" % ",".join(missing_fields))


def validate_params(data):
    try:
        data = json.loads(data)
        data['Rows'] = json.loads(data.get('Rows', '[{}]'))
        check_required_params(data)
    except ValueError:
        return None, "Decoding JSON has failed"
    except KeyError as e:
        return None, str(e)
    else:
        return data, None


@retry(ExceptionToCheck=(Exception,), max_retries=3, multiplier=2, logger=logger)
def insert_findings(findings, region, overbridge_cli=None):
    logger.info("inserting findings %d" % len(findings))
    if not overbridge_cli:
        overbridge_cli = boto3.client('overbridge', region_name=region)

    # import ipdb;ipdb.set_trace()
    resp = overbridge_cli.import_findings(
        Findings=findings
    )
    status_code = resp["ResponseMetadata"].get("HTTPStatusCode")
    failed_count = resp.get("FailedCount", 0)
    success_count = resp.get("SuccessCount")
    body = "FailedCount: %d SuccessCount: %d " % (
        failed_count, success_count)

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
    logger.info("event %s" % event)
    # import ipdb;ipdb.set_trace()
    data, err = validate_params(event.body)
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


if __name__ == '__main__':
    lambda_handler(None, None)
