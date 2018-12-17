import json
import os
import logging
from concurrent import futures
from datetime import datetime, timezone, timedelta
import dateutil.parser
import sys
sys.path.insert(0, '/opt')  # layer packages are in opt directory
import boto3

['_PY_TO_OP_NAME', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_cache', '_client_config', '_convert_to_request_dict', '_emit_api_params', '_endpoint', '_exceptions', '_exceptions_factory', '_get_waiter_config', '_load_exceptions', '_loader', '_make_api_call', '_register_handlers', '_request_signer', '_response_parser', '_serializer', '_service_model', 'accept_invitation', 'batch_disable_standards', 'batch_enable_standards', 'batch_import_findings', 'can_paginate', 'create_insight', 'create_members', 'decline_invitations', 'delete_insight', 'delete_invitations', 'delete_members', 'disable_import_findings_for_product', 'disable_security_hub', 'disassociate_from_master_account', 'disassociate_members', 'enable_import_findings_for_product', 'enable_security_hub', 'exceptions', 'generate_presigned_url', 'get_enabled_standards', 'get_findings', 'get_insight_results', 'get_insights', 'get_invitations_count', 'get_master_account', 'get_members', 'get_paginator', 'get_waiter', 'invite_members', 'list_enabled_products_for_import', 'list_invitations', 'list_members', 'meta', 'update_findings', 'update_insight', 'waiter_names']

FINDING_WINDOW_OFFSET = 5
NUM_WORKERS = 5
MAX_RESULTS = 100
ALLOWED_LOCKED_STATE_DAYS_THRESHOLD = 1


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

logger = get_logger()


def get_securityhub_region():
    lambda_region = os.getenv("AWS_REGION")
    securityhub_region = os.getenv("REGION", lambda_region)
    return securityhub_region


def get_product_subscription(arn):
    securityhub_region = get_securityhub_region()
    securityhub_cli = boto3.client('securityhub', region_name=securityhub_region)
    response = securityhub_cli.get_product_subscription(ProductSubscriptionArn=arn)
    return response


def generate_fixed_product_arns():
    securityhub_region = get_securityhub_region()
    yield [
        "arn:aws:securityhub:%s::product/aws/inspector" % securityhub_region,
        "arn:aws:securityhub:%s::product/aws/securityhub" % securityhub_region,
        "arn:aws:securityhub:%s:956882708938:product/sumologicinc/sumologic-mda" % securityhub_region,
        "arn:aws:securityhub:%s::product/aws/macie" % securityhub_region,
        "arn:aws:securityhub:%s::product/aws/guardduty" % securityhub_region
    ]


def get_product_arns(subscriptions):
    all_product_arns = []
    for subscription_arn in subscriptions:
        pre, account_id, product = subscription_arn.rsplit(':', 2)
        product = product.replace("product-subscription", "product")
        if product.startswith("product/aws/"):
            account_id = ""
        product_arn = f"{pre}:{account_id}:{product}"
        all_product_arns.append(product_arn)
    return all_product_arns


def generate_product_arns():
    securityhub_region = get_securityhub_region()
    securityhub_cli = boto3.client('securityhub', region_name=securityhub_region)
    has_next_page = True
    page_num = 0
    next_token = None
    params = {"MaxResults": MAX_RESULTS}
    while has_next_page:
        if next_token:
            params["NextToken"] = next_token
        resp = securityhub_cli.list_enabled_products_for_import(**params)
        next_token = resp.get('NextToken')
        subscriptions = resp["ProductSubscriptions"]
        has_next_page = next_token is not None
        page_num += 1
        logging.info("Generating ProductSubscriptions Page: %d" % page_num)
        yield get_product_arns(subscriptions)


def invoke_lambda(product_arn, start_date, last_date, last_event_date):
    region = os.getenv("AWS_REGION")
    lambda_cli = boto3.client('lambda', region_name=region)
    payload = bytes(json.dumps({
        "product_arn": product_arn,
        "start_date": start_date,
        "last_date": last_date,
        "last_event_date": last_event_date
    }), "utf-8")
    response = lambda_cli.invoke(
        FunctionName=os.getenv('SecurityHubCollectorFnName'),
        InvocationType='Event',
        Payload=payload
    )
    return response


def batch_insert_rows(dynamodbcli, rows, table_name):
    if len(rows) > 0:
        table = dynamodbcli.Table(table_name)
        with table.batch_writer() as batch:
            for item in rows:
                batch.put_item(Item=item)
        logger.info("Inserted Items into %s table Count: %d" % (
            table_name, len(rows)))


def batch_get_items_bypk(dynamodbcli, values, table_name, key="product_arn"):
    #Todo in future add pagination here currently len(values) <= 100
    response = dynamodbcli.batch_get_item(
        RequestItems={
            table_name: {
                'Keys': [{key: val} for val in set(values)],
                'ConsistentRead': True
            }
        },
        ReturnConsumedCapacity='TOTAL'
    )
    items = response['Responses'][table_name]
    logger.info("Fetched Items from %s table Count: %d UnprocessedKeys: %s" % (
        table_name, len(items), response["UnprocessedKeys"]))
    return items


def addminutes(date_obj, num_minutes):
    new_date_obj = date_obj + timedelta(minutes=num_minutes)
    return new_date_obj.isoformat()


def addmilliseconds(date_obj, num_millisecs):
    new_date_obj = date_obj + timedelta(milliseconds=num_millisecs)
    return new_date_obj.isoformat()


def get_current_datetime():
    return datetime.now(tz=timezone.utc)


def get_default_datetime():
    return datetime.fromtimestamp(0, timezone.utc)


def get_datetime_from_isoformat(date_str):
    return dateutil.parser.parse(date_str)


def is_lock_old(last_locked_date_str):
    last_locked_date = get_datetime_from_isoformat(last_locked_date_str)
    time_after_lock = get_current_datetime() - last_locked_date
    if time_after_lock.days >= ALLOWED_LOCKED_STATE_DAYS_THRESHOLD:
        return True

    return False


def get_rows(active_product_arns, existing_rows):
    existing_product_arn_map = {item["product_arn"]: item for item in existing_rows}
    existing_unlocked_rows = []
    existing_old_locked_rows = []
    non_existing_rows = []
    for arn in active_product_arns:
        if arn in existing_product_arn_map:
            row = existing_product_arn_map[arn]
            if int(row["is_locked"]) == 0:
                existing_unlocked_rows.append(row)
            elif is_lock_old(row["last_locked_date"]):
                row["is_locked"] = 0  # releasing locks on rows that remained locked for duration > 1 day (Ex lambda exits before releasing lock)
                existing_old_locked_rows.append(row)
        else:
            start_date = get_default_datetime().isoformat()
            non_existing_rows.append({
                "last_event_date": start_date,
                "last_locked_date": start_date,
                "is_locked": 0,
                "product_arn": arn
            })
    logger.info("Found Existing Unlocked Rows: %d, New Rows: %d, Old Locked Rows: %d" % (len(existing_unlocked_rows), len(non_existing_rows), len(existing_old_locked_rows)))
    logger.info("%s %s %s " % (non_existing_rows, existing_old_locked_rows, existing_unlocked_rows))
    return existing_unlocked_rows, existing_old_locked_rows, non_existing_rows


def create_tasks(unlocked_rows):
    # creating task here because otherwise needs to put condition to get start and last date only at 1st processor invocation as both of them needs to be fixed for subsequent invocations because of next token is sent with same params
    return [
        {
            "product_arn": row["product_arn"],
            "start_date": addmilliseconds(get_datetime_from_isoformat(row["last_event_date"]), 1),  # increasing time by one microsec to avoid duplicate findings
            "last_date": addminutes(get_current_datetime(), FINDING_WINDOW_OFFSET),
            "last_event_date": row["last_event_date"]
        } for row in unlocked_rows
    ]


def trigger_lambdas():
    lambda_region = os.getenv("AWS_REGION")
    lock_table_name = os.getenv("LOCK_TABLE")
    dynamodbcli = boto3.resource('dynamodb', region_name=lambda_region)

    all_futures = {}
    with futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        for product_arns in generate_fixed_product_arns():
            # fetching both locked/unlocked arns(no filtering) because then we won't know which arns doesn't exists
            existing_rows = batch_get_items_bypk(dynamodbcli, product_arns, lock_table_name)
            existing_unlocked_rows, existing_old_locked_rows, non_existing_rows = get_rows(product_arns, existing_rows)
            task_params = create_tasks(existing_unlocked_rows + non_existing_rows)
            batch_insert_rows(dynamodbcli, non_existing_rows + existing_old_locked_rows, lock_table_name)
            results = {executor.submit(invoke_lambda, **param): param['product_arn'] for param in task_params}
            all_futures.update(results)
        for future in futures.as_completed(all_futures):
            arn = all_futures[future]
            try:
                response = future.result()  # raises the exception instead of future.exception() which returns it
            except Exception as exc:
                logger.error('ProductArn: %r lambda generated an exception: %s' % (arn, exc))
            else:
                logger.info('ProductArn: %r lambda is scheduled StatusCode: %s' % (arn, response["ResponseMetadata"].get("HTTPStatusCode")))


def lambda_handler(event, context):
    logger.info("Invoking SecurityHubScheduler")
    trigger_lambdas()

if __name__ == '__main__':
    lambda_handler(None, None)

