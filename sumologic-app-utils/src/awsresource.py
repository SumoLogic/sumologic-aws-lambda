import ipaddress
import json
import os
import re
import time
from abc import abstractmethod

import traceback
import boto3
import six
from botocore.exceptions import ClientError
from resourcefactory import AutoRegisterResource
from retrying import retry


@six.add_metaclass(AutoRegisterResource)
class AWSResource(object):

    @abstractmethod
    def create(self, *args, **kwargs):
        pass

    @abstractmethod
    def update(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, *args, **kwargs):
        pass

    @abstractmethod
    def extract_params(self, event):
        pass


class AWSTrail(AWSResource):
    boolean_params = ["IncludeGlobalServiceEvents", "IsMultiRegionTrail", "EnableLogFileValidation",
                      "IsOrganizationTrail"]

    def __init__(self, props, *args, **kwargs):
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.cloudtrailcli = boto3.client('cloudtrail', region_name=self.region)

    def create(self, trail_name, params, *args, **kwargs):
        try:
            response = self.cloudtrailcli.create_trail(**params)
            print(f"Trail created {trail_name}")
            self.cloudtrailcli.start_logging(Name=trail_name)
            return {"TrailArn": response["TrailARN"]}, response["TrailARN"]
        except ClientError as e:
            print(f"Error in creating trail {e.response['Error']}")
            raise
        except Exception as e:
            print(f"Error in creating trail {e}")
            raise

    def update(self, old_trail_name, trail_name, params, *args, **kwargs):
        try:
            # Delete the trail if trail Name is changed.
            if old_trail_name != trail_name:
                return self.create(trail_name, params)
            else:
                response = self.cloudtrailcli.update_trail(**params)
                print(f"Trail updated {trail_name}")
                self.cloudtrailcli.start_logging(Name=trail_name)
                return {"TrailArn": response["TrailARN"]}, response["TrailARN"]
        except ClientError as e:
            print(f"Error in updating trail {e.response['Error']}")
            raise
        except Exception as e:
            print(f"Error in updating trail {e}")
            raise

    def delete(self, trail_name, *args, **kwargs):
        try:
            self.cloudtrailcli.delete_trail(
                Name=trail_name
            )
            print(f"Trail deleted {trail_name}")
        except ClientError as e:
            print(f"Error in deleting trail {e.response['Error']}")
            raise
        except Exception as e:
            print(f"Error in deleting trail {e}")
            raise

    def _transform_bool_values(self, k, v):
        if k in self.boolean_params:
            return True if v and v == "true" else False
        else:
            return v

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        parameters = ["S3BucketName", "S3KeyPrefix", "IncludeGlobalServiceEvents", "IsMultiRegionTrail",
                      "EnableLogFileValidation", "IsOrganizationTrail"]
        params = {k: self._transform_bool_values(k, v) for k, v in props.items() if k in parameters}
        params['Name'] = props.get("TrailName")

        # Get previous Trail Name
        old_trail_name = None
        if "OldResourceProperties" in event and "TrailName" in event['OldResourceProperties']:
            old_trail_name = event["OldResourceProperties"]['TrailName']

        return {
            "props": props,
            "trail_name": props.get("TrailName"),
            "params": params,
            "old_trail_name": old_trail_name
        }


class TagAWSResources(AWSResource):

    def __init__(self, props, *args, **kwargs):
        print(f'Tagging aws resource {props.get("AWSResource")}')

    def _tag_aws_resources(self, region_value, aws_resource, tags, account_id, delete_flag, filter_regex):
        # Get the class instance based on AWS Resource
        tag_resource = AWSResourcesProvider.get_provider(aws_resource, region_value, account_id)

        # Fetch and Filter the Resources.
        resources = tag_resource.fetch_resources()
        filtered_resources = tag_resource.filter_resources(filter_regex, resources)

        if filtered_resources:
            # Get the ARNs for all resources
            arns = tag_resource.get_arn_list(filtered_resources)

            # Tag or un-tag the resources.
            if delete_flag:
                tag_resource.delete_tags(arns, tags)
            else:
                tag_resource.add_tags(arns, tags)

    def create(self, region_value, aws_resource, tags, account_id, filter_regex, *args, **kwargs):
        print(f"TAG AWS RESOURCES - Starting the AWS resources Tag addition with Tags {tags}.")
        regions = [region_value]
        for region in regions:
            self._tag_aws_resources(region, aws_resource, tags, account_id, False, filter_regex)
        print("TAG AWS RESOURCES - Completed the AWS resources Tag addition.")

        return {"TAG_CREATION": "Successful"}, aws_resource

    def update(self, old_properties, region_value, aws_resource, tags, account_id, filter_regex, *args, **kwargs):
        # First Delete Old Tags from old aws resource with old filter regex and Then add new Tags.
        # Check if region or aws resource is changed, then create.
        if old_properties['Region'] != region_value or old_properties['AWSResource'] != aws_resource:
            data, aws_resource = self.create(region_value, aws_resource, tags, account_id, filter_regex)
        else:
            # If the region and aws resource is not changed, then check if any tag key is removed.
            # If yes, then delete only those tags.
            if tags and 'Tags' in old_properties and old_properties['Tags']:
                old_tags = old_properties['Tags']
                for tag_key in tags:
                    old_tags.pop(tag_key, None)
                if old_tags:
                    self.delete(old_properties['Region'], old_properties['AWSResource'], old_tags,
                                account_id, old_properties['Filter'], remove_on_delete_stack=True)

            print(f"TAG AWS RESOURCES - Starting the AWS resources Tag update with Tags {tags}.")
            regions = [region_value]
            for region in regions:
                self._tag_aws_resources(region, aws_resource, tags, account_id, False, filter_regex)

        print(f"updated tags for aws resource {aws_resource} ")
        return {"TAG_UPDATE": "Successful"}, aws_resource

    def delete(self, region_value, aws_resource, tags, account_id, filter_regex, remove_on_delete_stack, *args,
               **kwargs):
        tags_list = []
        if tags:
            tags_list = list(tags.keys())
        print(f"TAG AWS RESOURCES - Starting the AWS resources Tag deletion with Tags {tags_list}.")
        if remove_on_delete_stack:
            regions = [region_value]
            for region in regions:
                self._tag_aws_resources(region, aws_resource, tags, account_id, True, filter_regex)
            print("TAG AWS RESOURCES - Completed the AWS resources Tag deletion.")
        else:
            print("TAG AWS RESOURCES - Skipping AWS resources tags deletion.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        tags = {}
        if "Tags" in props:
            tags = props.get("Tags")

        old_properties = None
        if "OldResourceProperties" in event:
            old_properties = event["OldResourceProperties"]

        return {
            "region_value": props.get("Region"),
            "aws_resource": props.get("AWSResource"),
            "tags": tags,
            "account_id": props.get("AccountID"),
            "filter_regex": props.get("Filter"),
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack"),
            "old_properties": old_properties
        }


class EnableS3LogsResources(AWSResource):

    def __init__(self, props, *args, **kwargs):
        print(f'Enabling S3 for ALB/ELB-classic aws resource {props.get("AWSResource")}')

    def _s3_logs_alb_resources(self, region_value, aws_resource, bucket_name, bucket_prefix,
                               delete_flag, filter_regex, account_id):

        # Get the class instance based on AWS Resource
        tag_resource = AWSResourcesProvider.get_provider(aws_resource, region_value, account_id)

        # Fetch and Filter the Resources.
        resources = tag_resource.fetch_resources()
        if aws_resource != 'elb':
            filtered_resources = tag_resource.filter_resources(filter_regex, resources)
        else:
            filtered_resources = resources
        if filtered_resources:
            # Get the ARNs for all resources
            arns = tag_resource.get_arn_list(filtered_resources)

            # Enable and disable AWS ALB S3 the resources.
            if delete_flag:
                tag_resource.disable_s3_logs(arns, bucket_name)
            else:
                tag_resource.enable_s3_logs(arns, bucket_name, bucket_prefix)

    def create(self, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex,
               account_id, *args, **kwargs):
        print(f"ENABLE S3 LOGS - Starting the AWS resources S3 addition to bucket {bucket_name}.")
        self._s3_logs_alb_resources(region_value, aws_resource, bucket_name, bucket_prefix,
                                    False, filter_regex, account_id)
        print("ENABLE S3 LOGS - Completed the AWS resources S3 addition to bucket.")

        return {"S3_ENABLE": "Successful"}, aws_resource

    def update(self, old_properties, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, account_id, *args, **kwargs):
        # First Delete Old Tags from old aws resource with old filter regex and Then add new Tags.
        # Check if aws resource is changed, then raise exception.
        try:
            if old_properties['AWSResource'] != aws_resource:
                data, aws_resource = self.create(region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, account_id)
            else:
                # If bucket name or prefix are not same, delete the old logging.
                if old_properties['BucketName'] != bucket_name or old_properties['BucketPrefix'] != bucket_prefix:
                    self.delete(region_value, aws_resource, old_properties['BucketName'], old_properties['BucketPrefix'],
                                old_properties['Filter'], True, account_id)

                print(f"ENABLE S3 LOGS - Starting the AWS resources S3 Update with bucket {bucket_name}.")
                self._s3_logs_alb_resources(region_value, aws_resource, bucket_name, bucket_prefix,
                                            False, filter_regex, account_id)
            print("ENABLE S3 LOGS - Completed the AWS resources S3 Update for bucket.")
            return {"S3_ENABLE": "Successful"}, aws_resource
        except Exception as e:
            traceback.print_exc()
            raise

    def delete(self, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, remove_on_delete_stack,
               account_id, *args, **kwargs):
        if remove_on_delete_stack:
            self._s3_logs_alb_resources(region_value, aws_resource, bucket_name, bucket_prefix, True,
                                        filter_regex, account_id)
            print("ENABLE S3 LOGS - Completed the AWS resources S3 deletion to bucket.")
        else:
            print("ENABLE S3 LOGS - Skipping the AWS resources S3 deletion to bucket.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        old_properties = None
        if "OldResourceProperties" in event:
            old_properties = event["OldResourceProperties"]

        return {
            "region_value": os.environ.get("AWS_REGION"),
            "aws_resource": props.get("AWSResource"),
            "bucket_name": props.get("BucketName"),
            "bucket_prefix": props.get("BucketPrefix"),
            "filter_regex": props.get("Filter"),
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack"),
            "account_id": props.get("AccountID"),
            "old_properties": old_properties,
        }


class ConfigDeliveryChannel(AWSResource):

    def __init__(self, *args, **kwargs):
        self.config_client = boto3.client('config', region_name=os.environ.get("AWS_REGION"))

    def create_delivery_channel(self, delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn):
        name = "default"
        if not bucket_name:
            channels = self.config_client.describe_delivery_channels()
            if "DeliveryChannels" in channels:
                for channel in channels["DeliveryChannels"]:
                    bucket_name = channel["s3BucketName"]
                    if not bucket_prefix:
                        bucket_prefix = channel["s3KeyPrefix"] if "s3KeyPrefix" in channel else None
                    name = channel["name"]
                    break

        delivery_channel = {"name": name, "s3BucketName": bucket_name}

        if bucket_prefix:
            delivery_channel["s3KeyPrefix"] = bucket_prefix
        if sns_topic_arn:
            delivery_channel["snsTopicARN"] = sns_topic_arn
        if delivery_frequency:
            delivery_channel["configSnapshotDeliveryProperties"] = {'deliveryFrequency': delivery_frequency}

        self.config_client.put_delivery_channel(DeliveryChannel=delivery_channel)

        return name

    def create(self, delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn, *args, **kwargs):
        print(f"DELIVERY CHANNEL - Starting the AWS config Delivery channel create with bucket {bucket_name}.")

        name = self.create_delivery_channel(delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn)

        print("DELIVERY CHANNEL - Completed the AWS config Delivery channel create.")

        return {"DELIVERY_CHANNEL": "Successful"}, name

    def update(self, delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn, *args, **kwargs):
        print(f"updated delivery channel to {bucket_name} ")
        name = self.create_delivery_channel(delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn)
        return {"DELIVERY_CHANNEL": "Successful"}, name

    def delete(self, delivery_channel_name, bucket_name, delivery_frequency, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            if not bucket_name:
                self.create_delivery_channel(delivery_frequency, None, None, None)
            else:
                self.config_client.delete_delivery_channel(DeliveryChannelName=delivery_channel_name)
            print("DELIVERY CHANNEL - Completed the AWS Config delivery channel delete.")
        else:
            print("DELIVERY CHANNEL - Skipping the AWS Config delivery channel delete.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        delivery_channel_name = None
        if event.get('PhysicalResourceId'):
            _, delivery_channel_name = event['PhysicalResourceId'].split("/")

        return {
            "delivery_frequency": props.get("DeliveryFrequency"),
            "bucket_name": props.get("S3BucketName"),
            "bucket_prefix": props.get("S3KeyPrefix"),
            "sns_topic_arn": props.get("SnsTopicARN"),
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack"),
            "delivery_channel_name": delivery_channel_name
        }


def resource_tagging(event, context):
    print("AWS RESOURCE TAGGING :- Starting resource tagging")

    # Get Account Id and Alias from env.
    account_alias = os.environ.get("AccountAlias")
    account_id = os.environ.get("AccountID")
    filter_regex = os.environ.get("Filter")

    tags = {'account': account_alias}

    if "detail" in event:
        event_detail = event.get("detail")
        event_name = event_detail.get("eventName")
        region_value = event_detail.get("awsRegion")

        # Get the class instance based on Cloudtrail Event Name
        tag_resource = AWSResourcesProvider.get_provider(event_name, region_value, account_id)
        event_detail = tag_resource.filter_resources(filter_regex, event_detail)

        if event_detail:
            # Get the arns from the event.
            resources = tag_resource.get_arn_list_cloud_trail_event(event_detail)

            # Process the existing tags to add some more tags if necessary
            tags = tag_resource.process_tags(tags)

            # Tag the resources
            tag_resource.tag_resources_cloud_trail_event(resources, tags)

    print("AWS RESOURCE TAGGING :- Completed resource tagging")


def enable_s3_logs(event, context):
    print("AWS S3 ENABLE ALB :- Starting s3 logs enable")

    # Get Account Id and Alias from env.
    bucket_name = os.environ.get("BucketName")
    bucket_prefix = os.environ.get("BucketPrefix")
    account_id = os.environ.get("AccountID")
    filter_regex = os.environ.get("Filter")
    is_elbClassic = False
    if "detail" in event:
        event_detail = event.get("detail")
        event_name = event_detail.get("eventName")
        try:
            if(event_name=="CreateLoadBalancer" and event_detail.get("requestParameters").get("loadBalancerName")!=None):
                is_elbClassic=True
                event_name="ELBClassicCreate"
        except KeyError:
            print("Do Nothing")
        region_value = event_detail.get("awsRegion")

        # Get the class instance based on Cloudtrail Event Name
        if(not is_elbClassic):
            alb_resource = AWSResourcesProvider.get_provider(event_name, region_value, account_id)
            event_detail = alb_resource.filter_resources(filter_regex, event_detail)

            if event_detail:
                # Get the arns from the event.
                resources = alb_resource.get_arn_list_cloud_trail_event(event_detail)

                # Enable S3 logging
                alb_resource.enable_s3_logs(resources, bucket_name, bucket_prefix)
        else:
            elb_resource = AWSResourcesProvider.get_provider(event_name, region_value, account_id)
            event_detail = elb_resource.filter_resources(filter_regex, event_detail)
            if event_detail:
                resources = elb_resource.get_arn_list_cloud_trail_event(event_detail)
                elb_resource.enable_s3_logs(resources, bucket_name, bucket_prefix)

    print("AWS S3 ENABLE ALB :- Completed s3 logs enable")


@six.add_metaclass(AutoRegisterResource)
class AWSResourcesAbstract(object):
    event_resource_map = {
        "RunInstances": "ec2",
        "CreateStage": "apigateway",
        "CreateRestApi": "apigateway",
        "CreateDeployment": "apigateway",
        "CreateTable": "dynamodb",
        "CreateFunction20150331": "lambda",
        "CreateDBCluster": "rds",
        "CreateDBInstance": "rds",
        "CreateLoadBalancer": "elbv2",
        "CreateBucket": "s3",
        "ELBClassicCreate": "elb"
    }

    def __init__(self, aws_resource, region_value, account_id):
        self.region_value = region_value
        self.account_id = account_id

        # Get partition from boto3 session
        session = boto3.Session(region_name=region_value)
        self.partition = session.get_partition_for_region(region_value)

            # Initialize clients
        self.tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region_value)
        self.client = boto3.client(self.event_resource_map[aws_resource] if aws_resource in self.event_resource_map
                                   else aws_resource, region_name=region_value)

    @abstractmethod
    def fetch_resources(self):
        raise NotImplementedError()

    def filter_resources(self, filter_regex, resources):
        if filter_regex:
            pattern = re.compile(filter_regex)
            if isinstance(resources, list):
                filtered_resources = []
                for resource in resources:
                    matcher = pattern.search(str(resource))
                    if matcher:
                        filtered_resources.append(resource)

                return filtered_resources
            else:
                matcher = pattern.search(str(resources))
                if matcher:
                    return resources
                else:
                    return None
        return resources

    @abstractmethod
    def get_arn_list(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def process_tags(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def get_arn_list_cloud_trail_event(self, *args):
        raise NotImplementedError()

    @abstractmethod
    def tag_resources_cloud_trail_event(self, *args):
        raise NotImplementedError()

    def add_tags(self, arns, tags):
        if arns:
            chunk_records = self._batch_size_chunk(arns, 20)
            for record in chunk_records:
                self.tagging_client.tag_resources(ResourceARNList=record, Tags=tags)

    def delete_tags(self, arns, tags):
        if arns:
            chunk_records = self._batch_size_chunk(arns, 20)
            for record in chunk_records:
                self.tagging_client.untag_resources(ResourceARNList=record, TagKeys=list(tags.keys()))

    def _batch_size_chunk(self, iterable, size=1):
        length = len(iterable)
        for idx in range(0, length, size):
            data = iterable[idx:min(idx + size, length)]
            yield data

    @staticmethod
    def _apply_bucket_policy(bucket_name, statements):
        s3 = boto3.client('s3')
        for attempt in range(5):
            try:
                response = s3.get_bucket_policy(Bucket=bucket_name)
                existing_policy = json.loads(response["Policy"])
            except ClientError as e:
                if e.response['Error']['Code'] == "NoSuchBucketPolicy":
                    existing_policy = {"Version": "2012-10-17", "Statement": []}
                else:
                    raise
            existing_sids = {s.get("Sid") for s in existing_policy["Statement"] if s.get("Sid")}
            for stmt in statements:
                if stmt.get("Sid") not in existing_sids:
                    existing_policy["Statement"].append(stmt)
            try:
                s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(existing_policy))
                print(f"put_bucket_policy succeeded for {bucket_name} on attempt {attempt + 1}")
                return
            except ClientError as e:
                if e.response['Error']['Code'] == "OperationAborted":
                    print(f"OperationAborted on put_bucket_policy attempt {attempt + 1} for {bucket_name}, retrying in {2 ** attempt}s...")
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise Exception(f"Failed to put bucket policy for {bucket_name} after 5 attempts")


class EC2Resources(AWSResourcesAbstract):

    def fetch_resources(self):
        instances = []
        for page in self.client.get_paginator("describe_instances").paginate(MaxResults=1000):
            for reservation in page['Reservations']:
                if "Instances" in reservation:
                    instances.extend(reservation['Instances'])
        return instances

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                arns.append(
                    f"arn:{self.partition}:ec2:{self.region_value}:{self.account_id}:instance/{resource['InstanceId']}"
                )

        return arns

    def process_tags(self, tags):
        tags["Namespace"] = "AWS/EC2"

        tags_key_value = []
        for k, v in tags.items():
            tags_key_value.append({'Key': k, 'Value': v})

        return tags_key_value

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []
        response_elements = event_detail.get("responseElements")
        if response_elements and "instancesSet" in response_elements and "items" in response_elements.get(
                "instancesSet"):
            for item in response_elements.get("instancesSet").get("items"):
                if "instanceId" in item:
                    arns.append(item.get("instanceId"))

        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        self.client.create_tags(Resources=arns, Tags=tags)


class ApiGatewayResources(AWSResourcesAbstract):

    def fetch_resources(self):
        api_gateways = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.get_rest_apis(limit=500, position=next_token)
            else:
                response = self.client.get_rest_apis(limit=500)

            if "items" in response:
                api_gateways.extend(response["items"])
                for api in response["items"]:
                    id = api["id"]

                    stages = self.client.get_stages(restApiId=id)
                    for stage in stages["item"]:
                        stage["restApiId"] = id
                        api_gateways.append(stage)

            next_token = response["position"] if "position" in response else None

            if not next_token:
                next_token = 'END'

        return api_gateways

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                if "stageName" in resource:
                    arns.append(
                        f"arn:{self.partition}:apigateway:{self.region_value}::/restapis/{resource['restApiId']}/stages/{resource['stageName']}"
                    )
                else:
                    arns.append(f"arn:{self.partition}:apigateway:{self.region_value}::/restapis/{resource['id']}")

        return arns

    def process_tags(self, tags):
        return tags

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []
        event_name = event_detail.get("eventName")

        if "responseElements" in event_detail:
            response_elements = event_detail.get("responseElements")
            if response_elements and "self" in response_elements:
                details = response_elements.get("self")
                if event_name == "CreateStage":
                    arns.append(
                        f"arn:{self.partition}:apigateway:{self.region_value}::/restapis/{details.get('restApiId')}"
                        f"/stages/{details.get('stageName')}"
                    )

                elif event_name == "CreateRestApi":
                    arns.append(
                        f"arn:{self.partition}:apigateway:{self.region_value}::/restapis/{details.get('restApiId')}"
                    )

        if "requestParameters" in event_detail:
            request_parameters = event_detail.get("requestParameters")
            if request_parameters and "restApiId" in request_parameters \
                    and "createDeploymentInput" in request_parameters:
                details = request_parameters.get("createDeploymentInput")
                if event_name == "CreateDeployment":
                    arns.append(
                        f"arn:{self.partition}:apigateway:{self.region_value}::/restapis/"
                        f"{request_parameters.get('restApiId')}/stages/{details.get('stageName')}"
                    )

        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        for arn in arns:
            self.client.tag_resource(resourceArn=arn, tags=tags)


class DynamoDbResources(AWSResourcesAbstract):

    def fetch_resources(self):
        tables = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.list_tables(Limit=100, ExclusiveStartTableName=next_token)
            else:
                response = self.client.list_tables(Limit=100)

            if "TableNames" in response:
                tables.extend(response["TableNames"])

            next_token = response["LastEvaluatedTableName"] if "LastEvaluatedTableName" in response else None

            if not next_token:
                next_token = 'END'

        return tables

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                arns.append(
                    f"arn:{self.partition}:dynamodb:{self.region_value}:{self.account_id}:table/{resource}"
                )
        return arns

    def process_tags(self, tags):
        tags_key_value = []
        for k, v in tags.items():
            tags_key_value.append({'Key': k, 'Value': v})
        return tags_key_value

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []

        if "resources" in event_detail:
            for item in event_detail.get("resources"):
                if "ARN" in item:
                    arns.append(item.get("ARN"))
        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        for arn in arns:
            self.client.tag_resource(ResourceArn=arn, Tags=tags)


class LambdaResources(AWSResourcesAbstract):

    def fetch_resources(self):
        lambdas = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.list_functions(MaxItems=1000, Marker=next_token)
            else:
                response = self.client.list_functions(MaxItems=1000)

            if "Functions" in response:
                lambdas.extend(response["Functions"])

            next_token = response["NextMarker"] if "NextMarker" in response else None

            if not next_token:
                next_token = 'END'

        return lambdas

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                arns.append(resource["FunctionArn"])

        return arns

    def process_tags(self, tags):
        return tags

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []

        if "responseElements" in event_detail:
            response_elements = event_detail.get("responseElements")
            if response_elements and "functionArn" in response_elements:
                arns.append(response_elements.get("functionArn"))
        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        for arn in arns:
            self.client.tag_resource(Resource=arn, Tags=tags)


class RDSResources(AWSResourcesAbstract):

    def fetch_resources(self):
        resources = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.describe_db_clusters(MaxRecords=100, Marker=next_token)
            else:
                response = self.client.describe_db_clusters(MaxRecords=100)

            if "DBClusters" in response:
                resources.extend(response["DBClusters"])
                for function_name in response["DBClusters"]:
                    cluster_name = function_name['DBClusterIdentifier']
                    next_token = None
                    filters = [{'Name': 'db-cluster-id', 'Values': [cluster_name]}]
                    while next_token != 'END':
                        if next_token:
                            response_instances = self.client.describe_db_instances(MaxRecords=100, Marker=next_token,
                                                                                   Filters=filters)
                        else:
                            response_instances = self.client.describe_db_instances(MaxRecords=100, Filters=filters)

                        if "DBInstances" in response_instances:
                            resources.extend(response_instances["DBInstances"])

                        next_token = response_instances["Marker"] if "Marker" in response_instances else None

                        if not next_token:
                            next_token = 'END'

            next_token = response["Marker"] if "Marker" in response else None

            if not next_token:
                next_token = 'END'

        return resources

    def get_arn_list(self, resources):
        arns = {}
        if resources:
            for resource in resources:
                tags_key_value = []
                if "DBClusterIdentifier" in resource:
                    tags_key_value.append({'Key': "cluster", 'Value': resource['DBClusterIdentifier']})

                function_arn = None
                if "DBInstanceArn" in resource:
                    function_arn = resource["DBInstanceArn"]
                if "DBClusterArn" in resource:
                    function_arn = resource["DBClusterArn"]

                if function_arn in arns:
                    arns[function_arn].extend(tags_key_value)
                else:
                    arns[function_arn] = tags_key_value
        return arns

    def add_tags(self, arns, tags):
        if arns:
            for arn, tags_arn in arns.items():
                tags_key_value = self.process_tags(tags)
                tags_key_value.extend(tags_arn)
                self.client.add_tags_to_resource(ResourceName=arn, Tags=tags_key_value)

    def delete_tags(self, arns, tags):
        if arns:
            for arn, tags_arn in arns.items():
                tags_key_value = self.process_tags(tags)
                tags_key_value.extend(tags_arn)
                tags_keys = [sub['Key'] for sub in tags_key_value]
                self.client.remove_tags_from_resource(ResourceName=arn, TagKeys=tags_keys)

    def process_tags(self, tags):
        tags_key_value = []
        for k, v in tags.items():
            tags_key_value.append({'Key': k, 'Value': v})
        return tags_key_value

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = {}
        event_name = event_detail.get("eventName")
        tags_key_value = []

        if "responseElements" in event_detail:
            response_elements = event_detail.get("responseElements")
            if response_elements:
                if "dBClusterIdentifier" in response_elements:
                    tags_key_value.append({'Key': "cluster", 'Value': response_elements.get("dBClusterIdentifier")})

                if "dBClusterArn" in response_elements and event_name == "CreateDBCluster":
                    arns[response_elements.get("dBClusterArn")] = tags_key_value
                if "dBInstanceArn" in response_elements and event_name == "CreateDBInstance":
                    arns[response_elements.get("dBInstanceArn")] = tags_key_value
        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        for arn, tags_arn in arns.items():
            tags.extend(tags_arn)
            self.client.add_tags_to_resource(ResourceName=arn, Tags=tags)

class AlbResources(AWSResourcesAbstract):

    def add_bucket_policy(self, bucket_name):
        print("Adding policy to the bucket " + bucket_name)
        self._apply_bucket_policy(bucket_name, [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            },
            {
                "Sid": "AWSBucketExistenceCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:ListBucket",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSALBLogDeliveryAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "delivery.logs.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AddALBLogsStatement",
                "Effect": "Allow",
                "Principal": {"Service": "logdelivery.elasticloadbalancing.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}/*"
            }
        ])

    def fetch_resources(self):
        resources = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.describe_load_balancers(PageSize=400, Marker=next_token)
            else:
                response = self.client.describe_load_balancers(PageSize=400)

            if "LoadBalancers" in response:
                resources.extend(response['LoadBalancers'])

            next_token = response["NextMarker"] if "NextMarker" in response else None

            if not next_token:
                next_token = 'END'

        return resources

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                arns.append(resource['LoadBalancerArn'])
        return arns

    def process_tags(self, tags):
        tags_key_value = []
        for k, v in tags.items():
            tags_key_value.append({'Key': k, 'Value': v})

        return tags_key_value

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []
        response_elements = event_detail.get("responseElements")
        if response_elements and "loadBalancers" in response_elements:
            for item in response_elements.get("loadBalancers"):
                if "loadBalancerArn" in item:
                    arns.append(item.get("loadBalancerArn"))
        return arns

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, arns, tags):
        self.client.add_tags(ResourceArns=arns, Tags=tags)

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'true'},
                      {'Key': 'access_logs.s3.bucket', 'Value': s3_bucket},
                      {'Key': 'access_logs.s3.prefix', 'Value': s3_prefix}]

        for arn in arns:
            print("Enable S3 logging for ALB " + arn)
            response = self.client.describe_load_balancer_attributes(LoadBalancerArn=arn)
            if "Attributes" in response:
                for attribute in response["Attributes"]:
                    if attribute["Key"] == "access_logs.s3.enabled" and attribute["Value"] == "false":
                        try:
                            self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)
                            time.sleep(1)
                        except ClientError as e:
                            if "Error" in e.response and "Message" in e.response["Error"] \
                                    and "Access Denied for bucket" in e.response['Error']['Message']:
                                self.add_bucket_policy(s3_bucket)
                                time.sleep(10)
                                self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)
                            else:
                                raise e

    def disable_s3_logs(self, arns, s3_bucket):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'false'}]

        for arn in arns:
            response = self.client.describe_load_balancer_attributes(LoadBalancerArn=arn)
            if "Attributes" in response:
                for attribute in response["Attributes"]:
                    if attribute["Key"] == "access_logs.s3.bucket" and attribute["Value"] == s3_bucket:
                        self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)
                        time.sleep(1)

class S3Resource(AWSResourcesAbstract):

    def fetch_resources(self):
        resources = []
        response = self.client.list_buckets()

        if "Buckets" in response:
            resources.extend(response['Buckets'])

        return resources

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for bucket_detail in resources:
                bucket_name = bucket_detail["Name"]
                response = self.client.get_bucket_location(Bucket=bucket_name)
                if "LocationConstraint" in response:
                    location = response["LocationConstraint"]
                    if (location is None and self.region_value == "us-east-1") \
                            or (location and self.region_value in response["LocationConstraint"]):
                        arns.append(bucket_name)
        return arns

    def process_tags(self, tags):
        return tags

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []
        request_elements = event_detail.get("requestParameters")
        if request_elements and "bucketName" in request_elements:
            arns.append(request_elements.get("bucketName"))
        return arns

    def tag_resources_cloud_trail_event(self, *args):
        pass

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix):

        bucket_logging = {'LoggingEnabled': {'TargetBucket': s3_bucket, 'TargetPrefix': s3_prefix}}

        if arns:
            for bucket_name in arns:
                if bucket_name != s3_bucket:
                    response = self.client.get_bucket_logging(Bucket=bucket_name)
                    if not ("LoggingEnabled" in response and "TargetBucket" in response["LoggingEnabled"]):
                        try:
                            self.client.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus=bucket_logging)
                            time.sleep(1)
                        except ClientError as e:
                            if "Error" in e.response and "Message" in e.response["Error"] \
                                    and "InvalidTargetBucketForLogging" in e.response['Error']['Code']:
                                self.client.put_bucket_acl(
                                    Bucket=s3_bucket,
                                    GrantWrite='uri=http://acs.amazonaws.com/groups/s3/LogDelivery',
                                    GrantReadACP='uri=http://acs.amazonaws.com/groups/s3/LogDelivery'
                                )
                                time.sleep(20)
                                self.client.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus=bucket_logging)
                            else:
                                raise e

    def disable_s3_logs(self, arns, s3_bucket):
        if arns:
            for bucket_name in arns:
                response = self.client.get_bucket_logging(Bucket=bucket_name)
                if "LoggingEnabled" in response and "TargetBucket" in response["LoggingEnabled"] \
                        and response["LoggingEnabled"]["TargetBucket"] == s3_bucket:
                    self.client.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus={})
                    time.sleep(1)


class VpcResource(AWSResourcesAbstract):

    def __init__(self, aws_resource, region_value, account_id):
        super().__init__("ec2", region_value, account_id)
        self.aws_resource = aws_resource

    def fetch_resources(self):
        resources = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response, key = self.client.describe_vpcs(MaxResults=1000, NextToken=next_token)
            else:
                response = self.client.describe_vpcs(MaxResults=1000)

            if "Vpcs" in response:
                resources.extend(response["Vpcs"])

            next_token = response["NextToken"] if "NextToken" in response else None

            if not next_token:
                next_token = 'END'
        return resources

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                if "VpcId" in resource:
                    arns.append(resource["VpcId"])
        return arns

    def process_tags(self, tags):
        return tags

    def get_arn_list_cloud_trail_event(self, event_detail):
        arns = []
        response_elements = event_detail.get("responseElements")
        if response_elements:
            if "vpc" in response_elements and "vpcId" in response_elements["vpc"]:
                arns.append(response_elements["vpc"]["vpcId"])
        return arns

    def tag_resources_cloud_trail_event(self, *args):
        pass

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix):
        if arns:
            chunk_records = self._batch_size_chunk(arns, 1000)
            for record in chunk_records:
                response = self.client.create_flow_logs(
                    ResourceIds=record,
                    ResourceType='VPC',
                    TrafficType='ALL',
                    LogDestinationType='s3',
                    LogDestination=f"arn:{self.partition}:s3:::{s3_bucket}/{s3_prefix}"
                )
                print(response)
                if "*Access Denied for LogDestination*" in str(response):
                    self.add_bucket_policy(s3_bucket, s3_prefix)
                    time.sleep(10)
                    self.client.create_flow_logs(
                        ResourceIds=record,
                        ResourceType='VPC',
                        TrafficType='ALL',
                        LogDestinationType='s3',
                        LogDestination=f"arn:{self.partition}:s3:::{s3_bucket}/{s3_prefix}"
                    )

    def add_bucket_policy(self, bucket_name, prefix):
        print("Adding policy to the bucket " + bucket_name)
        self._apply_bucket_policy(bucket_name, [
            {
                "Sid": "AWSLogDeliveryAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "delivery.logs.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSLogDeliveryWrite",
                "Effect": "Allow",
                "Principal": {"Service": "delivery.logs.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}/{prefix}/AWSLogs/{self.account_id}/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            }
        ])

    def disable_s3_logs(self, arns, s3_bucket):
        if arns:
            chunk_records = self._batch_size_chunk(list(arns), 1000)
            for record in chunk_records:
                response = self.client.describe_flow_logs(Filters=[{'Name': 'resource-id', 'Values': record}])
                if response and "FlowLogs" in response:
                    flow_ids = []
                    for flow_logs in response["FlowLogs"]:
                        if "LogDestination" in flow_logs and s3_bucket in flow_logs["LogDestination"]:
                            flow_ids.append(flow_logs["FlowLogId"])
                    if flow_ids:
                        self.client.delete_flow_logs(FlowLogIds=flow_ids)


class ElbResource(AWSResourcesAbstract):
    def fetch_resources(self):
        resources = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.describe_load_balancers(PageSize=400, Marker=next_token)
            else:
                response = self.client.describe_load_balancers(PageSize=400)

            if "LoadBalancerDescriptions" in response:
                resources.extend(response['LoadBalancerDescriptions'])

            next_token = response["NextMarker"] if "NextMarker" in response else None

            if not next_token:
                next_token = 'END'

        return resources
    #there are no arn's associated with Classic elb
    def get_arn_list(self, resources):

        names = []
        if resources:
            for resource in resources:
                names.append(resource['LoadBalancerName'])
        return names

    def process_tags(self, tags):
        tags_key_value = []
        for k, v in tags.items():
            tags_key_value.append({'Key': k, 'Value': v})

        return tags_key_value

    def get_arn_list_cloud_trail_event(self, event_detail):
        lb_name = []
        request_parameters = event_detail.get("requestParameters")
        if request_parameters and "loadBalancerName" in request_parameters:
            lb_name.append(request_parameters.get("loadBalancerName"))
            return lb_name
        return None

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError), stop_max_attempt_number=10,
           wait_exponential_multiplier=2000, wait_exponential_max=10000)
    def tag_resources_cloud_trail_event(self, names, tags):
        self.client.add_tags(LoadBalancerNames=names, Tags=tags)

    def enable_s3_logs(self, names, s3_bucket, s3_prefix):
        for name in names:
            print("Enable S3 logging for ALB " + name)
            response = self.client.describe_load_balancer_attributes(LoadBalancerName=name)
            if "LoadBalancerAttributes" in response:
                access_logs = response.get("LoadBalancerAttributes").get("AccessLog")
                if not access_logs["Enabled"]:
                    access_logs["Enabled"] = True
                    access_logs["S3BucketName"] = s3_bucket
                    access_logs["S3BucketPrefix"] = s3_prefix
                    try:
                        self.client.modify_load_balancer_attributes(LoadBalancerName=name, LoadBalancerAttributes=response.get("LoadBalancerAttributes"))
                        time.sleep(10)
                    except ClientError as e:
                        if "Error" in e.response and "Message" in e.response["Error"] \
                            and "Access Denied for bucket" in e.response['Error']['Message']:
                            self.add_bucket_policy(s3_bucket)
                            time.sleep(10)
                            self.client.modify_load_balancer_attributes(LoadBalancerName=name, LoadBalancerAttributes=response.get("LoadBalancerAttributes"))
                        else:
                            raise e

    def add_bucket_policy(self, bucket_name):
        print("Adding policy to the bucket " + bucket_name)
        self._apply_bucket_policy(bucket_name, [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            },
            {
                "Sid": "AWSBucketExistenceCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:ListBucket",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSELBLogDeliveryAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "delivery.logs.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}"
            },
            {
                "Sid": "AddELBLogsStatement",
                "Effect": "Allow",
                "Principal": {"Service": "logdelivery.elasticloadbalancing.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:{self.partition}:s3:::{bucket_name}/*"
            }
        ])

    def disable_s3_logs(self, names, s3_bucket):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'false'}]

        for name in names:
            response = self.client.describe_load_balancer_attributes(LoadBalancerName=name)
            if "LoadBalancerAttributes" in response:
                access_logs = response.get("LoadBalancerAttributes").get("AccessLog")
                if access_logs["Enabled"]:
                    access_logs["Enabled"] = False
                    self.client.modify_load_balancer_attributes(LoadBalancerName=name, LoadBalancerAttributes=response.get("LoadBalancerAttributes"))
                    time.sleep(1)

class AWSResourcesProvider(object):
    provider_map = {
        "ec2": EC2Resources,
        "RunInstances": EC2Resources,
        "apigateway": ApiGatewayResources,
        "CreateStage": ApiGatewayResources,
        "CreateRestApi": ApiGatewayResources,
        "CreateDeployment": ApiGatewayResources,
        "dynamodb": DynamoDbResources,
        "CreateTable": DynamoDbResources,
        "lambda": LambdaResources,
        "CreateFunction20150331": LambdaResources,
        "rds": RDSResources,
        "CreateDBCluster": RDSResources,
        "CreateDBInstance": RDSResources,
        "elbv2": AlbResources,
        "CreateLoadBalancer": AlbResources,
        "s3": S3Resource,
        "CreateBucket": S3Resource,
        "vpc": VpcResource,
        "CreateVpc": VpcResource,
        "ELBClassicCreate": ElbResource,
        "elb": ElbResource,
    }

    @classmethod
    def get_provider(cls, provider_name, region_value, account_id, *args, **kwargs):
        if provider_name in cls.provider_map:
            return cls.provider_map[provider_name](provider_name, region_value, account_id)
        else:
            raise Exception(f"{provider_name} provider not found")


class AddBucketPolicy(AWSResource):
    """Custom::AddBucketPolicy — appends S3 log-delivery policy statements to an existing bucket
    without replacing any existing statements. Idempotent by Sid.
    ServiceType controls which statements are added: 'alb', 'elb', or 'cloudtrail'."""

    ALL_STATEMENTS = [
        {"Sid": "AWSCloudTrailAclCheck", "Effect": "Allow",
         "Principal": {"Service": "cloudtrail.amazonaws.com"},
         "Action": ["s3:GetBucketAcl"],
         "Resource": "arn:{partition}:s3:::{bucket}"},
        {"Sid": "AWSCloudTrailWrite", "Effect": "Allow",
         "Principal": {"Service": "cloudtrail.amazonaws.com"},
         "Action": ["s3:PutObject"],
         "Resource": "arn:{partition}:s3:::{bucket}/*",
         "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}},
        {"Sid": "AWSBucketExistenceCheck", "Effect": "Allow",
         "Principal": {"Service": "cloudtrail.amazonaws.com"},
         "Action": ["s3:ListBucket"],
         "Resource": "arn:{partition}:s3:::{bucket}"},
        {"Sid": "AWSALBLogDeliveryAclCheck", "Effect": "Allow",
         "Principal": {"Service": "delivery.logs.amazonaws.com"},
         "Action": ["s3:GetBucketAcl"],
         "Resource": "arn:{partition}:s3:::{bucket}"},
        {"Sid": "AddALBLogsStatement", "Effect": "Allow",
         "Principal": {"Service": "logdelivery.elasticloadbalancing.amazonaws.com"},
         "Action": ["s3:PutObject"],
         "Resource": "arn:{partition}:s3:::{bucket}/*"},
        {"Sid": "AWSELBLogDeliveryAclCheck", "Effect": "Allow",
         "Principal": {"Service": "delivery.logs.amazonaws.com"},
         "Action": ["s3:GetBucketAcl"],
         "Resource": "arn:{partition}:s3:::{bucket}"},
        {"Sid": "AddELBLogsStatement", "Effect": "Allow",
         "Principal": {"Service": "logdelivery.elasticloadbalancing.amazonaws.com"},
         "Action": ["s3:PutObject"],
         "Resource": "arn:{partition}:s3:::{bucket}/*"},
    ]

    SERVICE_SIDS = {
        "cloudtrail": {"AWSCloudTrailAclCheck", "AWSCloudTrailWrite", "AWSBucketExistenceCheck"},
        "alb":        {"AWSALBLogDeliveryAclCheck", "AddALBLogsStatement"},
        "elb":        {"AWSELBLogDeliveryAclCheck", "AddELBLogsStatement"},
    }

    def __init__(self, props, *args, **kwargs):
        self.props = props

    def _statements_for_service(self, service_type):
        allowed = self.SERVICE_SIDS.get(service_type)
        if not allowed:
            return self.ALL_STATEMENTS
        return [s for s in self.ALL_STATEMENTS if s["Sid"] in allowed]

    def _build_statements(self, bucket_name, partition, service_type):
        statements = []
        for tmpl in self._statements_for_service(service_type):
            stmt = json.loads(json.dumps(tmpl))
            stmt["Resource"] = stmt["Resource"].format(bucket=bucket_name, partition=partition)
            statements.append(stmt)
        return statements

    def _add_policy(self, bucket_name, partition, service_type):
        s3 = boto3.client('s3')
        expected_stmts = self._build_statements(bucket_name, partition, service_type)
        expected_sids = {s["Sid"] for s in expected_stmts}
        for attempt in range(5):
            try:
                response = s3.get_bucket_policy(Bucket=bucket_name)
                existing_policy = json.loads(response["Policy"])
            except ClientError as e:
                if e.response['Error']['Code'] == "NoSuchBucketPolicy":
                    existing_policy = {"Version": "2012-10-17", "Statement": []}
                else:
                    raise
            existing_sids = {s.get("Sid") for s in existing_policy["Statement"] if s.get("Sid")}
            added = []
            for stmt in expected_stmts:
                if stmt["Sid"] not in existing_sids:
                    existing_policy["Statement"].append(stmt)
                    added.append(stmt["Sid"])
            if added:
                print(f"put_bucket_policy attempt {attempt + 1} for {bucket_name}: adding SIDs {added}")
                try:
                    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(existing_policy))
                except ClientError as e:
                    if e.response['Error']['Code'] == "OperationAborted":
                        print(f"OperationAborted on put_bucket_policy attempt {attempt + 1} for {bucket_name}, retrying in {2 ** attempt}s...")
                        time.sleep(2 ** attempt)
                        continue
                    raise
                print(f"put_bucket_policy succeeded for {bucket_name} on attempt {attempt + 1}")
                # Verify our SIDs survived — a concurrent write could have overwritten them
                time.sleep(0.5 * (attempt + 1))
                verify = json.loads(s3.get_bucket_policy(Bucket=bucket_name)["Policy"])
                current_sids = {s.get("Sid") for s in verify["Statement"]}
                if not expected_sids.issubset(current_sids):
                    print(f"Concurrent policy overwrite detected on attempt {attempt + 1} for {bucket_name}, retrying...")
                    continue
            else:
                print(f"put_bucket_policy skipped for {bucket_name} on attempt {attempt + 1}: all SIDs already present")
            return added
        raise Exception(f"Failed to persist bucket policy for {bucket_name} after 5 attempts — concurrent overwrite")

    def _remove_policy(self, bucket_name, service_type):
        s3 = boto3.client('s3')
        our_sids = {s["Sid"] for s in self._statements_for_service(service_type)}
        try:
            response = s3.get_bucket_policy(Bucket=bucket_name)
            existing_policy = json.loads(response["Policy"])
        except ClientError as e:
            if e.response['Error']['Code'] in ("NoSuchBucketPolicy", "NoSuchBucket"):
                return
            raise
        existing_policy["Statement"] = [
            s for s in existing_policy["Statement"] if s.get("Sid") not in our_sids
        ]
        if existing_policy["Statement"]:
            s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(existing_policy))
        else:
            s3.delete_bucket_policy(Bucket=bucket_name)

    def create(self, bucket_name, partition, service_type, *args, **kwargs):
        added = self._add_policy(bucket_name, partition, service_type)
        return {"AddedSids": added, "BucketName": bucket_name}, bucket_name

    def update(self, bucket_name, partition, service_type, *args, **kwargs):
        added = self._add_policy(bucket_name, partition, service_type)
        return {"AddedSids": added, "BucketName": bucket_name}, bucket_name

    def delete(self, bucket_name, service_type, *args, **kwargs):
        self._remove_policy(bucket_name, service_type)
        return {"BucketName": bucket_name}, bucket_name

    def extract_params(self, event):
        props = event.get("ResourceProperties", {})
        return {
            "bucket_name": props.get("BucketName"),
            "partition": props.get("Partition", "aws"),
            "service_type": props.get("ServiceType", "").lower(),
        }


class ConfigureBucketNotifications(AWSResource):
    """Custom::ConfigureBucketNotifications — manages S3 event notifications and SNS subscriptions
    for all existing-bucket sources in one shot. Groups sources by bucket so that sources sharing
    the same bucket reuse a single SNS topic, avoiding S3's one-notification-per-event-type limit."""

    def __init__(self, props, *args, **kwargs):
        self.props = props

    def _get_topic_name(self, stack_id, bucket_name):
        import hashlib
        stack_suffix = stack_id.split('/')[-1].split('-')[0]
        bucket_hash = hashlib.sha256(bucket_name.encode("utf-8")).hexdigest()[:12]
        return "sumo-s3-notif-{}-{}".format(stack_suffix, bucket_hash)

    def _configure(self, sources, account_id, partition, stack_id, region):
        sns_client = boto3.client('sns', region_name=region)
        s3_client = boto3.client('s3', region_name=region)

        active = [s for s in sources if s.get('BucketName') and s.get('SumoEndpoint')]
        buckets = {}
        for src in active:
            seen = buckets.setdefault(src['BucketName'], {})
            seen[src['SumoEndpoint']] = True

        print("ConfigureBucketNotifications: {} unique bucket(s) to configure: {}".format(
            len(buckets), list(buckets.keys())))

        created_topics = {}
        for bucket_name, endpoints in buckets.items():
            topic_name = self._get_topic_name(stack_id, bucket_name)
            print("ConfigureBucketNotifications: creating/fetching SNS topic '{}' for bucket '{}'".format(
                topic_name, bucket_name))
            topic_arn = sns_client.create_topic(Name=topic_name)['TopicArn']
            print("ConfigureBucketNotifications: topic_arn={}".format(topic_arn))

            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "s3.amazonaws.com"},
                    "Action": "sns:Publish",
                    "Resource": topic_arn,
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {"aws:SourceArn": "arn:{}:s3:::{}".format(partition, bucket_name)}
                    }
                }]
            }
            sns_client.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName='Policy',
                AttributeValue=json.dumps(policy)
            )
            print("ConfigureBucketNotifications: SNS topic policy set for bucket '{}'".format(bucket_name))

            config = s3_client.get_bucket_notification_configuration(Bucket=bucket_name)
            config.pop('ResponseMetadata', None)
            existing_topic_arns = [tc.get('TopicArn') for tc in config.get('TopicConfigurations', [])]
            print("ConfigureBucketNotifications: existing TopicConfigurations on bucket '{}': {}".format(
                bucket_name, existing_topic_arns))

            overlapping_events = {'s3:ObjectCreated:Put', 's3:ObjectCreated:*'}
            kept = []
            removed = []
            for tc in config.get('TopicConfigurations', []):
                if set(tc.get('Events', [])).intersection(overlapping_events):
                    removed.append(tc.get('TopicArn'))
                else:
                    kept.append(tc)
            if removed:
                print("ConfigureBucketNotifications: removed {} conflicting TopicConfiguration(s) "
                      "on bucket '{}': {}".format(len(removed), bucket_name, removed))
            kept.append({'TopicArn': topic_arn, 'Events': ['s3:ObjectCreated:Put']})
            config['TopicConfigurations'] = kept
            print("ConfigureBucketNotifications: overwriting S3 notification on bucket '{}' — "
                  "retained {} existing config(s), added topic_arn={}".format(
                      bucket_name, len(kept) - 1, topic_arn))
            s3_client.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration=config,
            )
            print("ConfigureBucketNotifications: S3 notification updated for bucket '{}'".format(
                bucket_name))

            for endpoint in endpoints:
                sns_client.subscribe(TopicArn=topic_arn, Protocol='https', Endpoint=endpoint)
                print("ConfigureBucketNotifications: subscribed endpoint '{}' to topic '{}'".format(
                    endpoint, topic_arn))

            created_topics[bucket_name] = topic_arn

        print("ConfigureBucketNotifications: done. created_topics={}".format(created_topics))
        return created_topics

    def _cleanup(self, sources, account_id, partition, stack_id, region):
        sns_client = boto3.client('sns', region_name=region)
        s3_client = boto3.client('s3', region_name=region)

        active = [s for s in sources if s.get('BucketName') and s.get('SumoEndpoint')]
        buckets = {}
        for src in active:
            seen = buckets.setdefault(src['BucketName'], {})
            seen[src['SumoEndpoint']] = True

        print("ConfigureBucketNotifications: {} unique bucket(s) to clean up: {}".format(
            len(buckets), list(buckets.keys())))

        for bucket_name in buckets:
            topic_name = self._get_topic_name(stack_id, bucket_name)
            topic_arn = "arn:{}:sns:{}:{}:{}".format(partition, region, account_id, topic_name)
            print("ConfigureBucketNotifications: processing bucket='{}' topic_arn={}".format(
                bucket_name, topic_arn))

            try:
                config = s3_client.get_bucket_notification_configuration(Bucket=bucket_name)
                config.pop('ResponseMetadata', None)
                before = [tc.get('TopicArn') for tc in config.get('TopicConfigurations', [])]
                config['TopicConfigurations'] = [
                    tc for tc in config.get('TopicConfigurations', []) if tc.get('TopicArn') != topic_arn
                ]
                after = [tc.get('TopicArn') for tc in config['TopicConfigurations']]
                print("ConfigureBucketNotifications: overwriting S3 notification on bucket '{}' — "
                      "before={}, after={}".format(bucket_name, before, after))
                s3_client.put_bucket_notification_configuration(
                    Bucket=bucket_name,
                    NotificationConfiguration=config,
                )
                print("ConfigureBucketNotifications: S3 notification updated for bucket '{}'".format(
                    bucket_name))
            except ClientError as e:
                print("ConfigureBucketNotifications: skipping S3 notification removal for bucket '{}' — "
                      "{}".format(bucket_name, e.response['Error']))

            try:
                paginator = sns_client.get_paginator('list_subscriptions_by_topic')
                for page in paginator.paginate(TopicArn=topic_arn):
                    for sub in page.get('Subscriptions', []):
                        if sub['SubscriptionArn'] not in ('PendingConfirmation', 'Deleted'):
                            sns_client.unsubscribe(SubscriptionArn=sub['SubscriptionArn'])
                            print("ConfigureBucketNotifications: unsubscribed {}".format(
                                sub['SubscriptionArn']))
            except ClientError as e:
                print("ConfigureBucketNotifications: skipping subscription removal for topic '{}' — "
                      "{}".format(topic_arn, e.response['Error']))

            try:
                sns_client.delete_topic(TopicArn=topic_arn)
                print("ConfigureBucketNotifications: deleted SNS topic '{}'".format(topic_arn))
            except ClientError as e:
                print("ConfigureBucketNotifications: skipping topic deletion for '{}' — "
                      "{}".format(topic_arn, e.response['Error']))

    def create(self, sources, account_id, partition, stack_id, region, *args, **kwargs):
        self._configure(sources, account_id, partition, stack_id, region)
        resource_id = "BucketNotifications-{}".format(stack_id.split('/')[-1].split('-')[0])
        return {}, resource_id

    def update(self, sources, account_id, partition, stack_id, region,
               old_sources=None, *args, **kwargs):
        if old_sources:
            self._cleanup(old_sources, account_id, partition, stack_id, region)
        self._configure(sources, account_id, partition, stack_id, region)
        resource_id = "BucketNotifications-{}".format(stack_id.split('/')[-1].split('-')[0])
        return {}, resource_id

    def delete(self, sources, account_id, partition, stack_id, region, *args, **kwargs):
        self._cleanup(sources, account_id, partition, stack_id, region)
        return {}, None

    def extract_params(self, event):
        props = event.get("ResourceProperties", {})
        params = {
            "sources": props.get("Sources", []),
            "account_id": props.get("AccountId"),
            "partition": props.get("Partition"),
            "stack_id": props.get("StackId"),
            "region": props.get("Region"),
        }
        old_props = event.get("OldResourceProperties", {})
        if old_props:
            params["old_sources"] = old_props.get("Sources", [])
        return params


class ElasticIPLookup(AWSResource):
    """Returns the public IP of an existing Elastic IP allocation. Nothing is created or deleted."""

    def __init__(self, props, *args, **kwargs):
        self.ec2_client = boto3.client('ec2', region_name=os.environ.get("AWS_REGION"))

    def _lookup(self, allocation_id):
        response = self.ec2_client.describe_addresses(AllocationIds=[allocation_id])
        addresses = response.get("Addresses", [])
        if not addresses or not addresses[0].get("PublicIp"):
            raise Exception(f"ELASTIC IP LOOKUP - Elastic IP allocation {allocation_id} not found.")
        return addresses[0]["PublicIp"]

    def create(self, allocation_id, *args, **kwargs):
        public_ip = self._lookup(allocation_id)
        print(f"ELASTIC IP LOOKUP - Allocation {allocation_id} has public IP {public_ip}.")
        return {"PublicIp": public_ip}, allocation_id

    def update(self, allocation_id, *args, **kwargs):
        return self.create(allocation_id)

    def delete(self, *args, **kwargs):
        print("ELASTIC IP LOOKUP - Nothing to delete.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        return {
            "allocation_id": props.get("AllocationId"),
        }


class NetworkSSMOutputs(object):
    """
    SSM parameters under /sumologic/awso/network written by the static outbound IP network setup. Everything written
    is tagged with CreatedBy, SumoStackId and SumoVpcId so that inputs published by customers can be told apart from
    outputs, and so that delete removes only what this stack wrote. nat-public-ip is written last, AWSO treats the
    setup as configured only once it exists. Needs self.ssm_client.
    """
    CREATED_BY = "sumologic-awso"
    OUTPUT_NAMES = ("vpc-id", "private-subnet-ids", "security-group-id", "nat-public-ip")

    def _is_stack_written(self, parameter_name, stack_id=None, vpc_id=None):
        """True when the SSM parameter carries the tags this resource writes (not a customer input)."""
        response = self.ssm_client.list_tags_for_resource(ResourceType="Parameter", ResourceId=parameter_name)
        tags = {tag["Key"]: tag["Value"] for tag in response.get("TagList", [])}
        if tags.get("CreatedBy") != self.CREATED_BY:
            return False
        return (stack_id is None or tags.get("SumoStackId") == stack_id) and (vpc_id is None or tags.get("SumoVpcId") == vpc_id)

    def _write_outputs(self, prefix, values, customer_inputs, stack_id, vpc_id):
        tags = [{"Key": "CreatedBy", "Value": self.CREATED_BY}, {"Key": "SumoStackId", "Value": stack_id},
                {"Key": "SumoVpcId", "Value": vpc_id}]
        for name in self.OUTPUT_NAMES:
            if name in customer_inputs:
                continue
            parameter_name = f"{prefix}/{name}"
            self.ssm_client.put_parameter(Name=parameter_name, Value=values[name], Overwrite=True,
                                          Type="StringList" if name == "private-subnet-ids" else "String")
            self.ssm_client.add_tags_to_resource(ResourceType="Parameter", ResourceId=parameter_name, Tags=tags)
            print(f"VPC NETWORK SETUP - Wrote SSM parameter {parameter_name}.")

    def _delete_outputs(self, prefix, stack_id, vpc_id):
        for name in self.OUTPUT_NAMES:
            parameter_name = f"{prefix}/{name}"
            try:
                if self._is_stack_written(parameter_name, stack_id, vpc_id):
                    self.ssm_client.delete_parameter(Name=parameter_name)
                    print(f"VPC NETWORK SETUP - Deleted SSM parameter {parameter_name}.")
            except ClientError as e:
                if e.response["Error"]["Code"] not in ("ParameterNotFound", "InvalidResourceId"):
                    raise


class VPCNetworkSetup(NetworkSSMOutputs, AWSResource):
    """
    Validates an existing VPC for static outbound IP (Lambda -> private subnet -> NAT gateway -> IGW) and creates
    only the missing components. Resources created here are tagged with CreatedBy, SumoStackId and SumoVpcId so that
    delete removes only those resources and never touches customer-owned resources.
    """
    SUBNET_PREFIX_LENGTH = 28
    PRIVATE_SUBNET_COUNT = 2
    MAX_EXISTING_SUBNETS = 3
    PHYSICAL_ID_PREFIX = "vpcnet-"
    # SSM parameters under the prefix: customers may publish INPUT_NAMES, this resource writes OUTPUT_NAMES
    # (tagged) except the ones the customer already published. nat-public-ip is written last, AWSO treats the setup
    # as configured only once it exists.
    INPUT_NAMES = ("vpc-id", "private-subnet-ids", "elastic-ip-allocation-id", "security-group-id")

    def __init__(self, props, *args, **kwargs):
        self.ec2_client = boto3.client('ec2', region_name=os.environ.get("AWS_REGION"))
        self.ssm_client = boto3.client('ssm', region_name=os.environ.get("AWS_REGION"))

    # ---------- SSM inputs ----------
    def _read_inputs(self, prefix):
        """Customer published inputs. Parameters written by this resource (tagged) are not inputs."""
        names = [f"{prefix}/{name}" for name in self.INPUT_NAMES]
        response = self.ssm_client.get_parameters(Names=names)
        inputs = {}
        for parameter in response.get("Parameters", []):
            if not self._is_stack_written(parameter["Name"]):
                inputs[parameter["Name"].rsplit("/", 1)[-1]] = parameter["Value"].strip()
        return inputs

    # ---------- helpers ----------
    def _tags(self, stack_id, vpc_id, name):
        return [
            {"Key": "Name", "Value": f"sumologic-awso-{name}"},
            {"Key": "CreatedBy", "Value": self.CREATED_BY},
            {"Key": "SumoStackId", "Value": stack_id},
            {"Key": "SumoVpcId", "Value": vpc_id},
        ]

    def _tag_spec(self, resource_type, stack_id, vpc_id, name):
        return [{"ResourceType": resource_type, "Tags": self._tags(stack_id, vpc_id, name)}]

    def _owned_filters(self, stack_id, vpc_id):
        return [
            {"Name": "tag:CreatedBy", "Values": [self.CREATED_BY]},
            {"Name": "tag:SumoStackId", "Values": [stack_id]},
            {"Name": "tag:SumoVpcId", "Values": [vpc_id]},
        ]

    def _is_owned(self, resource, stack_id, vpc_id):
        # Re-check tags client side so a customer owned resource is never deleted.
        tags = {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}
        return (tags.get("CreatedBy") == self.CREATED_BY and tags.get("SumoStackId") == stack_id
                and tags.get("SumoVpcId") == vpc_id)

    def _route_table_for_subnet(self, vpc_id, subnet_id):
        response = self.ec2_client.describe_route_tables(
            Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}])
        if response.get("RouteTables"):
            return response["RouteTables"][0]
        response = self.ec2_client.describe_route_tables(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}, {"Name": "association.main", "Values": ["true"]}])
        return response["RouteTables"][0] if response.get("RouteTables") else None

    @staticmethod
    def _default_route_target(route_table, key, prefix):
        if not route_table:
            return None
        for route in route_table.get("Routes", []):
            if route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get("State") == "active":
                target = route.get(key, "")
                if target.startswith(prefix):
                    return target
        return None

    def _get_vpc_subnets(self, vpc_id):
        subnets = []
        paginator = self.ec2_client.get_paginator('describe_subnets')
        for page in paginator.paginate(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]):
            subnets.extend(page.get("Subnets", []))
        return subnets

    def _get_public_nat_gateways(self, vpc_id):
        response = self.ec2_client.describe_nat_gateways(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}, {"Name": "state", "Values": ["available"]}])
        return [nat for nat in response.get("NatGateways", []) if nat.get("ConnectivityType", "public") == "public"]

    def _nat_public_ips(self, nat_ids):
        if not nat_ids:
            return []
        response = self.ec2_client.describe_nat_gateways(NatGatewayIds=list(nat_ids))
        ips = []
        for nat in response.get("NatGateways", []):
            for address in nat.get("NatGatewayAddresses", []):
                if address.get("PublicIp") and address["PublicIp"] not in ips:
                    ips.append(address["PublicIp"])
        return ips

    def _free_cidrs(self, vpc_id, count):
        vpc = self.ec2_client.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
        vpc_cidrs = [ipaddress.ip_network(assoc["CidrBlock"]) for assoc in vpc.get("CidrBlockAssociationSet", [])
                     if assoc.get("CidrBlockState", {}).get("State") == "associated"]
        used = [ipaddress.ip_network(subnet["CidrBlock"]) for subnet in self._get_vpc_subnets(vpc_id)]
        free = []
        for vpc_cidr in vpc_cidrs:
            if vpc_cidr.prefixlen > self.SUBNET_PREFIX_LENGTH:
                continue
            for candidate in vpc_cidr.subnets(new_prefix=self.SUBNET_PREFIX_LENGTH):
                if not any(candidate.overlaps(existing) for existing in used + free):
                    free.append(candidate)
                    if len(free) == count:
                        return [str(cidr) for cidr in free]
        raise Exception(f"VPC NETWORK SETUP - VPC {vpc_id} does not have {count} free /{self.SUBNET_PREFIX_LENGTH} "
                        f"CIDR range(s). Add a secondary CIDR block to the VPC or provide existing private subnet IDs.")

    def _availability_zones(self, count):
        response = self.ec2_client.describe_availability_zones(
            Filters=[{"Name": "state", "Values": ["available"]}, {"Name": "zone-type", "Values": ["availability-zone"]}])
        zones = sorted(zone["ZoneName"] for zone in response.get("AvailabilityZones", []))
        return zones[:count]

    # ---------- validation of supplied inputs ----------
    def _validate_vpc(self, vpc_id):
        if not re.match(r"^vpc-[0-9a-f]+$", vpc_id or ""):
            raise Exception(f"VPC NETWORK SETUP - VPC ID '{vpc_id}' is not valid, expected vpc-xxxx.")
        try:
            vpcs = self.ec2_client.describe_vpcs(VpcIds=[vpc_id]).get("Vpcs", [])
        except ClientError as e:
            raise Exception(f"VPC NETWORK SETUP - VPC {vpc_id} not found: {e}")
        if not vpcs:
            raise Exception(f"VPC NETWORK SETUP - VPC {vpc_id} not found.")
        for attribute in ("enableDnsSupport", "enableDnsHostnames"):
            value = self.ec2_client.describe_vpc_attribute(VpcId=vpc_id, Attribute=attribute)
            key = attribute[0].upper() + attribute[1:]
            if attribute == "enableDnsSupport" and not value[key]["Value"]:
                raise Exception(f"VPC NETWORK SETUP - VPC {vpc_id} has DNS support disabled, Lambda cannot resolve "
                                f"Sumo Logic API host names. Enable DNS support on the VPC.")

    def _validate_eip(self, allocation_id, nat_ids):
        try:
            addresses = self.ec2_client.describe_addresses(AllocationIds=[allocation_id]).get("Addresses", [])
        except ClientError as e:
            raise Exception(f"VPC NETWORK SETUP - Elastic IP {allocation_id} not found: {e}")
        if not addresses:
            raise Exception(f"VPC NETWORK SETUP - Elastic IP {allocation_id} not found.")
        if nat_ids:
            nat_allocations = set()
            for nat in self.ec2_client.describe_nat_gateways(NatGatewayIds=list(nat_ids)).get("NatGateways", []):
                nat_allocations.update(address.get("AllocationId") for address in nat.get("NatGatewayAddresses", []))
            if allocation_id not in nat_allocations:
                raise Exception(f"VPC NETWORK SETUP - Elastic IP {allocation_id} does not belong to NAT gateway(s) "
                                f"{sorted(nat_ids)} used by the VPC. Use the NAT gateway Elastic IP or remove the "
                                f"Elastic IP input.")

    def _validate_security_group(self, vpc_id, security_group_id):
        try:
            groups = self.ec2_client.describe_security_groups(GroupIds=[security_group_id]).get("SecurityGroups", [])
        except ClientError as e:
            raise Exception(f"VPC NETWORK SETUP - Security group {security_group_id} not found: {e}")
        if not groups:
            raise Exception(f"VPC NETWORK SETUP - Security group {security_group_id} not found.")
        group = groups[0]
        if group["VpcId"] != vpc_id:
            raise Exception(f"VPC NETWORK SETUP - Security group {security_group_id} does not belong to VPC {vpc_id}.")
        for rule in group.get("IpPermissionsEgress", []):
            open_cidr = any(ip_range.get("CidrIp") == "0.0.0.0/0" for ip_range in rule.get("IpRanges", []))
            protocol = rule.get("IpProtocol")
            covers_443 = protocol == "-1" or (protocol == "tcp" and rule.get("FromPort", 0) <= 443 <= rule.get("ToPort", 0))
            if open_cidr and covers_443:
                return
        raise Exception(f"VPC NETWORK SETUP - Security group {security_group_id} does not allow outbound tcp/443 to "
                        f"0.0.0.0/0. Add the rule or remove the security group input.")

    def _create_security_group(self, vpc_id, stack_id):
        # create is re-run on stack update, reuse the group this stack already created
        existing = self.ec2_client.describe_security_groups(Filters=self._owned_filters(stack_id, vpc_id))
        for group in existing.get("SecurityGroups", []):
            if self._is_owned(group, stack_id, vpc_id):
                print(f"VPC NETWORK SETUP - Using security group {group['GroupId']} created earlier.")
                return group["GroupId"]
        group_id = self.ec2_client.create_security_group(
            GroupName=f"sumologic-awso-lambda-{stack_id.split('/')[-1][:8]}",
            Description="SumoLogic AWS Observability Lambda functions - outbound HTTPS to Sumo Logic APIs",
            VpcId=vpc_id, TagSpecifications=self._tag_spec("security-group", stack_id, vpc_id, "lambda-sg"))["GroupId"]
        self.ec2_client.authorize_security_group_egress(GroupId=group_id, IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
            "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS to Sumo Logic APIs"}]}])
        try:
            self.ec2_client.revoke_security_group_egress(GroupId=group_id, IpPermissions=[{
                "IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        except ClientError:
            print("VPC NETWORK SETUP - Default egress rule was not found on the security group.")
        print(f"VPC NETWORK SETUP - Created security group {group_id}.")
        return group_id

    # ---------- discovery / creation steps ----------
    def _validate_given_subnets(self, vpc_id, subnet_ids):
        response = self.ec2_client.describe_subnets(SubnetIds=subnet_ids)
        nat_ids = []
        for subnet in response.get("Subnets", []):
            if subnet["VpcId"] != vpc_id:
                raise Exception(f"VPC NETWORK SETUP - Subnet {subnet['SubnetId']} does not belong to VPC {vpc_id}.")
            nat_id = self._default_route_target(self._route_table_for_subnet(vpc_id, subnet["SubnetId"]),
                                                "NatGatewayId", "nat-")
            if not nat_id:
                raise Exception(f"VPC NETWORK SETUP - Subnet {subnet['SubnetId']} does not route 0.0.0.0/0 to a NAT "
                                f"gateway. Add the route or remove the subnet from the input.")
            nat_ids.append(nat_id)
        return nat_ids

    def _find_nat_routed_subnets(self, vpc_id, available_nat_ids):
        selected, nat_ids, zones = [], [], set()
        for subnet in self._get_vpc_subnets(vpc_id):
            if subnet["AvailabilityZone"] in zones:
                continue
            nat_id = self._default_route_target(self._route_table_for_subnet(vpc_id, subnet["SubnetId"]),
                                                "NatGatewayId", "nat-")
            if nat_id and nat_id in available_nat_ids:
                selected.append(subnet["SubnetId"])
                nat_ids.append(nat_id)
                zones.add(subnet["AvailabilityZone"])
                if len(selected) == self.MAX_EXISTING_SUBNETS:
                    break
        return selected, nat_ids

    def _ensure_internet_gateway(self, vpc_id, stack_id):
        response = self.ec2_client.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}])
        if response.get("InternetGateways"):
            igw_id = response["InternetGateways"][0]["InternetGatewayId"]
            print(f"VPC NETWORK SETUP - Using existing internet gateway {igw_id}.")
            return igw_id
        igw_id = self.ec2_client.create_internet_gateway(
            TagSpecifications=self._tag_spec("internet-gateway", stack_id, vpc_id, "igw"))["InternetGateway"]["InternetGatewayId"]
        self.ec2_client.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        print(f"VPC NETWORK SETUP - Created internet gateway {igw_id}.")
        return igw_id

    def _ensure_public_subnet(self, vpc_id, igw_id, stack_id):
        for subnet in self._get_vpc_subnets(vpc_id):
            if self._default_route_target(self._route_table_for_subnet(vpc_id, subnet["SubnetId"]),
                                          "GatewayId", "igw-"):
                print(f"VPC NETWORK SETUP - Using existing public subnet {subnet['SubnetId']}.")
                return subnet["SubnetId"]
        cidr = self._free_cidrs(vpc_id, 1)[0]
        subnet_id = self.ec2_client.create_subnet(
            VpcId=vpc_id, CidrBlock=cidr, AvailabilityZone=self._availability_zones(1)[0],
            TagSpecifications=self._tag_spec("subnet", stack_id, vpc_id, "public-subnet"))["Subnet"]["SubnetId"]
        route_table_id = self.ec2_client.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=self._tag_spec("route-table", stack_id, vpc_id, "public-rt"))["RouteTable"]["RouteTableId"]
        self.ec2_client.create_route(RouteTableId=route_table_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
        self.ec2_client.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
        print(f"VPC NETWORK SETUP - Created public subnet {subnet_id} ({cidr}).")
        return subnet_id

    def _ensure_nat_gateway(self, vpc_id, allocation_id, stack_id):
        nat_gateways = self._get_public_nat_gateways(vpc_id)
        if nat_gateways:
            nat_id = nat_gateways[0]["NatGatewayId"]
            print(f"VPC NETWORK SETUP - Using existing NAT gateway {nat_id}.")
            return nat_id
        igw_id = self._ensure_internet_gateway(vpc_id, stack_id)
        public_subnet_id = self._ensure_public_subnet(vpc_id, igw_id, stack_id)
        if not allocation_id:
            allocation_id = self.ec2_client.allocate_address(
                Domain="vpc", TagSpecifications=self._tag_spec("elastic-ip", stack_id, vpc_id, "nat-eip"))["AllocationId"]
            print(f"VPC NETWORK SETUP - Allocated Elastic IP {allocation_id}.")
        nat_id = self.ec2_client.create_nat_gateway(
            SubnetId=public_subnet_id, AllocationId=allocation_id,
            TagSpecifications=self._tag_spec("natgateway", stack_id, vpc_id, "nat"))["NatGateway"]["NatGatewayId"]
        print(f"VPC NETWORK SETUP - Creating NAT gateway {nat_id}, waiting for it to become available.")
        self.ec2_client.get_waiter("nat_gateway_available").wait(
            NatGatewayIds=[nat_id], WaiterConfig={"Delay": 15, "MaxAttempts": 40})
        return nat_id

    def _create_private_subnets(self, vpc_id, nat_id, stack_id):
        zones = self._availability_zones(self.PRIVATE_SUBNET_COUNT)
        cidrs = self._free_cidrs(vpc_id, len(zones))
        route_table_id = self.ec2_client.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=self._tag_spec("route-table", stack_id, vpc_id, "private-rt"))["RouteTable"]["RouteTableId"]
        self.ec2_client.create_route(RouteTableId=route_table_id, DestinationCidrBlock="0.0.0.0/0", NatGatewayId=nat_id)
        subnet_ids = []
        for index, (zone, cidr) in enumerate(zip(zones, cidrs)):
            subnet_id = self.ec2_client.create_subnet(
                VpcId=vpc_id, CidrBlock=cidr, AvailabilityZone=zone,
                TagSpecifications=self._tag_spec("subnet", stack_id, vpc_id, f"private-subnet-{index + 1}"))["Subnet"]["SubnetId"]
            self.ec2_client.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
            subnet_ids.append(subnet_id)
            print(f"VPC NETWORK SETUP - Created private subnet {subnet_id} ({cidr}) in {zone}.")
        return subnet_ids

    # ---------- CloudFormation handlers ----------
    @staticmethod
    def _split(value):
        return [item.strip() for item in (value or "").split(",") if item.strip()]

    def create(self, vpc_id, allocation_id, private_subnet_ids, stack_id, ssm_prefix=None, security_group_id=None,
               *args, **kwargs):
        # Direct inputs (single account) win over the ones customers publish in SSM Parameter Store (StackSets).
        customer_inputs = {}
        if ssm_prefix:
            customer_inputs = self._read_inputs(ssm_prefix)
            if not vpc_id:
                vpc_id = customer_inputs.get("vpc-id")
            if not private_subnet_ids:
                private_subnet_ids = self._split(customer_inputs.get("private-subnet-ids"))
            if not allocation_id:
                allocation_id = customer_inputs.get("elastic-ip-allocation-id")
            if not security_group_id:
                security_group_id = customer_inputs.get("security-group-id")
        if not vpc_id:
            raise Exception(f"VPC NETWORK SETUP - VPC ID is required for ExistingVPC. Provide the VPC ID parameter or "
                            f"publish it in SSM parameter {ssm_prefix}/vpc-id in this account and region "
                            f"({os.environ.get('AWS_REGION')}).")

        print(f"VPC NETWORK SETUP - Starting network validation for VPC {vpc_id}.")
        self._validate_vpc(vpc_id)
        if security_group_id:
            self._validate_security_group(vpc_id, security_group_id)

        if private_subnet_ids:
            subnet_ids = private_subnet_ids
            nat_ids = self._validate_given_subnets(vpc_id, subnet_ids)
            if allocation_id:
                self._validate_eip(allocation_id, set(nat_ids))
        else:
            if allocation_id:
                self._validate_eip(allocation_id, None)
            nat_gateways = self._get_public_nat_gateways(vpc_id)
            available_nat_ids = [nat["NatGatewayId"] for nat in nat_gateways]
            if allocation_id and available_nat_ids:
                self._validate_eip(allocation_id, set(available_nat_ids))
            subnet_ids, nat_ids = self._find_nat_routed_subnets(vpc_id, available_nat_ids)
            if subnet_ids:
                print(f"VPC NETWORK SETUP - Using existing NAT routed private subnets {subnet_ids}.")
            else:
                nat_id = self._ensure_nat_gateway(vpc_id, allocation_id, stack_id)
                subnet_ids = self._create_private_subnets(vpc_id, nat_id, stack_id)
                nat_ids = [nat_id]

        if not security_group_id:
            security_group_id = self._create_security_group(vpc_id, stack_id)
        nat_public_ips = self._nat_public_ips(set(nat_ids))
        data = {"VpcId": vpc_id, "SubnetIds": ",".join(subnet_ids), "SecurityGroupId": security_group_id,
                "NatPublicIp": ",".join(nat_public_ips)}
        if ssm_prefix:
            self._write_outputs(ssm_prefix, {"vpc-id": vpc_id, "private-subnet-ids": data["SubnetIds"],
                                             "security-group-id": security_group_id,
                                             "nat-public-ip": data["NatPublicIp"]},
                                customer_inputs, stack_id, vpc_id)
        print(f"VPC NETWORK SETUP - Completed. Subnets {subnet_ids}, NAT public IP(s) {nat_public_ips}.")
        return data, f"{self.PHYSICAL_ID_PREFIX}{vpc_id}"

    def update(self, vpc_id, allocation_id, private_subnet_ids, stack_id, ssm_prefix=None, security_group_id=None,
               old_properties=None, *args, **kwargs):
        # A different VPC returns a new physical id, CloudFormation then sends delete for the old VPC resources.
        # For the same VPC the create is idempotent because each step discovers before creating.
        return self.create(vpc_id, allocation_id, private_subnet_ids, stack_id, ssm_prefix, security_group_id)

    def delete(self, stack_id, physical_id=None, ssm_prefix=None, vpc_id=None, *args, **kwargs):
        # The VPC id comes from the physical id, the properties or SSM inputs may have changed or been removed.
        # main.py returns the physical id as <LogicalResourceId>/vpcnet-<vpc-id>
        resource_id = (physical_id or "").rsplit("/", 1)[-1]
        if resource_id.startswith(self.PHYSICAL_ID_PREFIX):
            vpc_id = resource_id[len(self.PHYSICAL_ID_PREFIX):]
        if not vpc_id:
            print("VPC NETWORK SETUP - No VPC id found, nothing to delete.")
            return
        print(f"VPC NETWORK SETUP - Deleting resources created for VPC {vpc_id}.")
        filters = self._owned_filters(stack_id, vpc_id)

        def owned(resources):
            return [resource for resource in resources if self._is_owned(resource, stack_id, vpc_id)]

        nat_ids = [nat["NatGatewayId"] for nat in owned(self.ec2_client.describe_nat_gateways(Filters=filters).get("NatGateways", []))
                   if nat["State"] not in ("deleted", "deleting")]
        for nat_id in nat_ids:
            self.ec2_client.delete_nat_gateway(NatGatewayId=nat_id)
            print(f"VPC NETWORK SETUP - Deleting NAT gateway {nat_id}.")
        self._wait_nat_deleted(nat_ids)

        for address in owned(self.ec2_client.describe_addresses(Filters=filters).get("Addresses", [])):
            self.ec2_client.release_address(AllocationId=address["AllocationId"])
            print(f"VPC NETWORK SETUP - Released Elastic IP {address['AllocationId']}.")

        for route_table in owned(self.ec2_client.describe_route_tables(Filters=filters).get("RouteTables", [])):
            for association in route_table.get("Associations", []):
                if not association.get("Main"):
                    self.ec2_client.disassociate_route_table(AssociationId=association["RouteTableAssociationId"])
            self.ec2_client.delete_route_table(RouteTableId=route_table["RouteTableId"])
            print(f"VPC NETWORK SETUP - Deleted route table {route_table['RouteTableId']}.")

        for subnet in owned(self.ec2_client.describe_subnets(Filters=filters).get("Subnets", [])):
            self._delete_subnet(subnet["SubnetId"])

        for igw in owned(self.ec2_client.describe_internet_gateways(Filters=filters).get("InternetGateways", [])):
            for attachment in igw.get("Attachments", []):
                self.ec2_client.detach_internet_gateway(InternetGatewayId=igw["InternetGatewayId"], VpcId=attachment["VpcId"])
            self.ec2_client.delete_internet_gateway(InternetGatewayId=igw["InternetGatewayId"])
            print(f"VPC NETWORK SETUP - Deleted internet gateway {igw['InternetGatewayId']}.")

        for group in owned(self.ec2_client.describe_security_groups(Filters=filters).get("SecurityGroups", [])):
            self._delete_security_group(group["GroupId"])

        if ssm_prefix:
            self._delete_outputs(ssm_prefix, stack_id, vpc_id)
        print("VPC NETWORK SETUP - Completed deletion.")

    def _wait_nat_deleted(self, nat_ids, timeout=600):
        deadline = time.time() + timeout
        while nat_ids and time.time() < deadline:
            response = self.ec2_client.describe_nat_gateways(NatGatewayIds=nat_ids)
            if all(nat["State"] == "deleted" for nat in response.get("NatGateways", [])):
                return
            time.sleep(15)

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError) and exc.response["Error"]["Code"] == "DependencyViolation",
           stop_max_delay=300000, wait_fixed=20000)
    def _delete_subnet(self, subnet_id):
        # Lambda ENIs can take a few minutes to release after the function is deleted.
        self.ec2_client.delete_subnet(SubnetId=subnet_id)
        print(f"VPC NETWORK SETUP - Deleted subnet {subnet_id}.")

    @retry(retry_on_exception=lambda exc: isinstance(exc, ClientError) and exc.response["Error"]["Code"] == "DependencyViolation",
           stop_max_delay=300000, wait_fixed=20000)
    def _delete_security_group(self, group_id):
        # Lambda ENIs keep the security group in use until they are released.
        self.ec2_client.delete_security_group(GroupId=group_id)
        print(f"VPC NETWORK SETUP - Deleted security group {group_id}.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        old_properties = event.get("OldResourceProperties")
        params = {
            "stack_id": props.get("StackId"),
            "ssm_prefix": props.get("SSMPrefix"),
        }
        if event.get("RequestType") == "Delete":
            # delete is driven by the physical id, not by inputs that may no longer exist
            params["physical_id"] = event.get("PhysicalResourceId", "")
            params["vpc_id"] = props.get("VpcId")
        else:
            params.update({
                "vpc_id": props.get("VpcId"),
                "allocation_id": props.get("ElasticIPAllocationId"),
                "private_subnet_ids": self._split(props.get("PrivateSubnetIds")),
                "security_group_id": props.get("SecurityGroupId"),
                "old_properties": old_properties,
            })
        return params


class NetworkSSMParameters(NetworkSSMOutputs, AWSResource):
    """
    Writes the SSM parameters of the NewVPC static outbound IP network. AWS::SSM::Parameter fails with a name
    conflict when the parameter already exists (left by a deleted stack, or published by the populate script), so the
    parameters are written here with overwrite. A parameter owned by another live network stack is never taken over.
    """
    PHYSICAL_ID_PREFIX = "ssmnet-"

    def __init__(self, props, *args, **kwargs):
        self.ssm_client = boto3.client('ssm', region_name=os.environ.get("AWS_REGION"))
        self.cfn_client = boto3.client('cloudformation', region_name=os.environ.get("AWS_REGION"))

    def _owner_stack_id(self, parameter_name):
        """Stack id from the tags this resource writes, None when the parameter is absent or has no owner."""
        try:
            self.ssm_client.get_parameter(Name=parameter_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return None
            raise
        response = self.ssm_client.list_tags_for_resource(ResourceType="Parameter", ResourceId=parameter_name)
        tags = {tag["Key"]: tag["Value"] for tag in response.get("TagList", [])}
        return tags.get("SumoStackId") if tags.get("CreatedBy") == self.CREATED_BY else None

    def _is_live_stack(self, stack_id):
        try:
            stacks = self.cfn_client.describe_stacks(StackName=stack_id).get("Stacks", [])
        except ClientError as e:
            if "does not exist" in e.response["Error"].get("Message", ""):
                return False
            raise
        return any(stack["StackStatus"] != "DELETE_COMPLETE" for stack in stacks)

    def create(self, vpc_id, private_subnet_ids, security_group_id, nat_public_ip, stack_id, ssm_prefix, *args, **kwargs):
        # Check every parameter before writing any, a failure must leave the existing ones untouched.
        for name in self.OUTPUT_NAMES:
            owner = self._owner_stack_id(f"{ssm_prefix}/{name}")
            if owner and owner != stack_id and self._is_live_stack(owner):
                raise Exception(f"NETWORK SSM PARAMETERS - {ssm_prefix}/{name} belongs to stack {owner}, which still "
                                f"exists. Delete that stack first, or deploy only one static outbound IP network per "
                                f"account and region.")
        # A stale nat-public-ip paired with new values would make AWSO see a half written network. Remove it first,
        # AWSO then reports "Not configured" until it is written again, last.
        stale = f"{ssm_prefix}/nat-public-ip"
        if self._owner_stack_id(stale) != stack_id:
            try:
                self.ssm_client.delete_parameter(Name=stale)
                print(f"NETWORK SSM PARAMETERS - Removed existing {stale}.")
            except ClientError as e:
                # The role may delete only tagged parameters. An untagged one is overwritten by the write below.
                if e.response["Error"]["Code"] not in ("ParameterNotFound", "AccessDeniedException"):
                    raise
        self._write_outputs(ssm_prefix, {"vpc-id": vpc_id, "private-subnet-ids": private_subnet_ids,
                                         "security-group-id": security_group_id, "nat-public-ip": nat_public_ip},
                            {}, stack_id, vpc_id)
        return {"NatPublicIp": nat_public_ip}, f"{self.PHYSICAL_ID_PREFIX}{vpc_id}"

    def update(self, *args, **kwargs):
        # Idempotent, create overwrites the parameters this stack owns.
        return self.create(*args, **kwargs)

    def delete(self, stack_id, ssm_prefix, physical_id=None, vpc_id=None, *args, **kwargs):
        # main.py returns the physical id as <LogicalResourceId>/ssmnet-<vpc-id>
        resource_id = (physical_id or "").rsplit("/", 1)[-1]
        if resource_id.startswith(self.PHYSICAL_ID_PREFIX):
            vpc_id = resource_id[len(self.PHYSICAL_ID_PREFIX):]
        if not vpc_id or not ssm_prefix:
            print("NETWORK SSM PARAMETERS - No VPC id found, nothing to delete.")
            return
        self._delete_outputs(ssm_prefix, stack_id, vpc_id)

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        params = {"stack_id": props.get("StackId"), "ssm_prefix": props.get("SSMPrefix")}
        if event.get("RequestType") == "Delete":
            params["physical_id"] = event.get("PhysicalResourceId", "")
            params["vpc_id"] = props.get("VpcId")
        else:
            params.update({
                "vpc_id": props.get("VpcId"),
                "private_subnet_ids": props.get("PrivateSubnetIds"),
                "security_group_id": props.get("SecurityGroupId"),
                "nat_public_ip": props.get("NatPublicIp"),
            })
        return params


if __name__ == '__main__':
    params = {"AWSResource": "s3"}
    # value = ConfigDeliveryChannel()
    # value.create("Six_Hours", "config-bucket-668508221233", "config", "")

    value = EnableS3LogsResources(params)
    # value.create("us-east-2", "s3", "sadasdasdasd-us-east-2", "s3logs/", "", "", "")
    value.delete("us-east-2", "s3", "sadasdasdasd-us-east-2", "s3logs", "", True, "")
