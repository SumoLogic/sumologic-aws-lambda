import json
import os
import re
import time
from abc import abstractmethod

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
            print("Trail created %s" % trail_name)
            self.cloudtrailcli.start_logging(Name=trail_name)
            return {"TrailArn": response["TrailARN"]}, response["TrailARN"]
        except ClientError as e:
            print("Error in creating trail %s" % e.response['Error'])
            raise
        except Exception as e:
            print("Error in creating trail %s" % e)
            raise

    def update(self, trail_name, params, *args, **kwargs):
        try:
            response = self.cloudtrailcli.update_trail(**params)
            print("Trail updated %s" % trail_name)
            self.cloudtrailcli.start_logging(Name=trail_name)
            return {"TrailArn": response["TrailARN"]}, response["TrailARN"]
        except ClientError as e:
            print("Error in updating trail %s" % e.response['Error'])
            raise
        except Exception as e:
            print("Error in updating trail %s" % e)
            raise

    def delete(self, trail_name, *args, **kwargs):
        try:
            self.cloudtrailcli.delete_trail(
                Name=trail_name
            )
            print("Trail deleted %s" % trail_name)
        except ClientError as e:
            print("Error in deleting trail %s" % e.response['Error'])
            raise
        except Exception as e:
            print("Error in deleting trail %s" % e)
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
        return {
            "props": props,
            "trail_name": props.get("TrailName"),
            "params": params
        }


class TagAWSResources(AWSResource):

    def __init__(self, props, *args, **kwargs):
        print('Tagging aws resource %s' % props.get("AWSResource"))

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
        print("TAG AWS RESOURCES - Starting the AWS resources Tag addition with Tags %s." % tags)
        regions = [region_value]
        for region in regions:
            self._tag_aws_resources(region, aws_resource, tags, account_id, False, filter_regex)
        print("TAG AWS RESOURCES - Completed the AWS resources Tag addition.")

        return {"TAG_CREATION": "Successful"}, "Tag"

    def update(self, region_value, aws_resource, tags, account_id, filter_regex, *args, **kwargs):
        self.create(region_value, aws_resource, tags, account_id, filter_regex, *args, **kwargs)
        print("updated tags for aws resource %s " % aws_resource)
        return {"TAG_UPDATE": "Successful"}, "Tag"

    def delete(self, region_value, aws_resource, tags, account_id, filter_regex, remove_on_delete_stack, *args,
               **kwargs):
        tags_list = []
        if tags:
            tags_list = list(tags.keys())
        print("TAG AWS RESOURCES - Starting the AWS resources Tag deletion with Tags %s." % tags_list)
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
        return {
            "region_value": props.get("Region"),
            "aws_resource": props.get("AWSResource"),
            "tags": tags,
            "account_id": props.get("AccountID"),
            "filter_regex": props.get("Filter"),
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack")
        }


class EnableS3LogsResources(AWSResource):

    def __init__(self, props, *args, **kwargs):
        print('Enabling S3 for ALB aws resource %s' % props.get("AWSResource"))

    def _s3_logs_alb_resources(self, region_value, aws_resource, bucket_name, bucket_prefix,
                               delete_flag, filter_regex, region_account_id, account_id):

        # Get the class instance based on AWS Resource
        tag_resource = AWSResourcesProvider.get_provider(aws_resource, region_value, account_id)

        # Fetch and Filter the Resources.
        resources = tag_resource.fetch_resources()
        filtered_resources = tag_resource.filter_resources(filter_regex, resources)

        if filtered_resources:
            # Get the ARNs for all resources
            arns = tag_resource.get_arn_list(filtered_resources)

            # Enable and disable AWS ALB S3 the resources.
            if delete_flag:
                tag_resource.disable_s3_logs(arns, bucket_name)
            else:
                tag_resource.enable_s3_logs(arns, bucket_name, bucket_prefix, region_account_id)

    def create(self, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, region_account_id,
               account_id, *args, **kwargs):
        print("ENABLE S3 LOGS - Starting the AWS resources S3 addition to bucket %s." % bucket_name)
        self._s3_logs_alb_resources(region_value, aws_resource, bucket_name, bucket_prefix,
                                    False, filter_regex, region_account_id, account_id)
        print("ENABLE S3 LOGS - Completed the AWS resources S3 addition to bucket.")

        return {"S3_ENABLE": "Successful"}, "S3"

    def update(self, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, region_account_id,
               account_id, *args, **kwargs):
        self.create(region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, region_account_id,
                    account_id, *args, **kwargs)
        print("updated S3 bucket to %s " % bucket_name)
        return {"S3_ENABLE": "Successful"}, "S3"

    def delete(self, region_value, aws_resource, bucket_name, bucket_prefix, filter_regex, remove_on_delete_stack,
               account_id, *args, **kwargs):
        if remove_on_delete_stack:
            self._s3_logs_alb_resources(region_value, aws_resource, bucket_name, bucket_prefix, True,
                                        filter_regex, "", account_id)
            print("ENABLE S3 LOGS - Completed the AWS resources S3 deletion to bucket.")
        else:
            print("ENABLE S3 LOGS - Skipping the AWS resources S3 deletion to bucket.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        return {
            "region_value": os.environ.get("AWS_REGION"),
            "aws_resource": props.get("AWSResource"),
            "bucket_name": props.get("BucketName"),
            "bucket_prefix": props.get("BucketPrefix"),
            "filter_regex": props.get("Filter"),
            "region_account_id": props.get("RegionAccountId"),
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack"),
            "account_id": props.get("AccountID")
        }


class ConfigDeliveryChannel(AWSResource):

    def __init__(self, *args, **kwargs):
        self.config_client = boto3.client('config', region_name=os.environ.get("AWS_REGION"))

    def create(self, delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn, *args, **kwargs):
        print("DELIVERY CHANNEL - Starting the AWS config Delivery channel create with bucket %s." % bucket_name)

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

        print("DELIVERY CHANNEL - Completed the AWS config Delivery channel create.")

        return {"DELIVERY_CHANNEL": "Successful"}, name

    def update(self, delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn, *args, **kwargs):
        print("updated delivery channel to %s " % bucket_name)
        return self.create(delivery_frequency, bucket_name, bucket_prefix, sns_topic_arn, *args, **kwargs)

    def delete(self, delivery_channel_name, bucket_name, delivery_frequency, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            if not bucket_name:
                self.create(delivery_frequency, None, None, None)
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
    region_account_id = os.environ.get("RegionAccountId")

    if "detail" in event:
        event_detail = event.get("detail")
        event_name = event_detail.get("eventName")
        region_value = event_detail.get("awsRegion")

        # Get the class instance based on Cloudtrail Event Name
        alb_resource = AWSResourcesProvider.get_provider(event_name, region_value, account_id)
        event_detail = alb_resource.filter_resources(filter_regex, event_detail)

        if event_detail:
            # Get the arns from the event.
            resources = alb_resource.get_arn_list_cloud_trail_event(event_detail)

            # Enable S3 logging
            alb_resource.enable_s3_logs(resources, bucket_name, bucket_prefix, region_account_id)

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
        "CreateBucket": "s3"
    }

    def __init__(self, aws_resource, region_value, account_id):
        self.tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region_value)
        self.client = boto3.client(self.event_resource_map[aws_resource] if aws_resource in self.event_resource_map
                                   else aws_resource, region_name=region_value)
        self.region_value = region_value
        self.account_id = account_id

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


class EC2Resources(AWSResourcesAbstract):

    def fetch_resources(self):
        instances = []
        next_token = None
        while next_token != 'END':
            if next_token:
                response = self.client.describe_instances(MaxResults=1000, NextToken=next_token)
            else:
                response = self.client.describe_instances(MaxResults=1000)

            for reservation in response['Reservations']:
                if "Instances" in reservation:
                    instances.extend(reservation['Instances'])

            next_token = response["NextToken"] if "NextToken" in response else None

            if not next_token:
                next_token = 'END'

        return instances

    def get_arn_list(self, resources):
        arns = []
        if resources:
            for resource in resources:
                arns.append(
                    "arn:aws:ec2:" + self.region_value + ":" + self.account_id + ":instance/" + resource['InstanceId'])

        return arns

    def process_tags(self, tags):
        tags["namespace"] = "hostmetrics"

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
                    arns.append("arn:aws:apigateway:" + self.region_value + "::/restapis/" + resource["restApiId"]
                                + "/stages/" + resource["stageName"])
                else:
                    arns.append("arn:aws:apigateway:" + self.region_value + "::/restapis/" + resource["id"])

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
                    arns.append("arn:aws:apigateway:" + self.region_value + "::/restapis/"
                                + details.get("restApiId") + "/stages/"
                                + details.get("stageName"))
                elif event_name == "CreateRestApi":
                    arns.append("arn:aws:apigateway:" + self.region_value + "::/restapis/"
                                + details.get("restApiId"))

        if "requestParameters" in event_detail:
            request_parameters = event_detail.get("requestParameters")
            if request_parameters and "restApiId" in request_parameters \
                    and "createDeploymentInput" in request_parameters:
                details = request_parameters.get("createDeploymentInput")
                if event_name == "CreateDeployment":
                    arns.append("arn:aws:apigateway:" + self.region_value + "::/restapis/"
                                + request_parameters.get("restApiId") + "/stages/"
                                + details.get("stageName"))
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
                arns.append("arn:aws:dynamodb:" + self.region_value + ":" + self.account_id + ":table/" + resource)

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

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix, elb_region_account_id):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'true'},
                      {'Key': 'access_logs.s3.bucket', 'Value': s3_bucket},
                      {'Key': 'access_logs.s3.prefix', 'Value': s3_prefix}]

        for arn in arns:
            response = self.client.describe_load_balancer_attributes(LoadBalancerArn=arn)
            if "Attributes" in response:
                for attribute in response["Attributes"]:
                    if attribute["Key"] == "access_logs.s3.enabled" and attribute["Value"] == "false":
                        try:
                            self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)
                        except ClientError as e:
                            if "Error" in e.response and "Message" in e.response["Error"] \
                                    and "Access Denied for bucket" in e.response['Error']['Message']:
                                self.add_bucket_policy(s3_bucket, elb_region_account_id)
                                self.enable_s3_logs(arns, s3_bucket, s3_prefix, elb_region_account_id)
                            else:
                                raise e

    def add_bucket_policy(self, bucket_name, elb_region_account_id):
        print("Adding policy to the bucket " + bucket_name)
        s3 = boto3.client('s3')
        try:
            response = s3.get_bucket_policy(Bucket=bucket_name)
            existing_policy = json.loads(response["Policy"])
        except ClientError as e:
            if "Error" in e.response and "Code" in e.response["Error"] \
                    and e.response['Error']['Code'] == "NoSuchBucketPolicy":
                existing_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                    ]
                }
            else:
                raise e

        bucket_policy = {
            'Sid': 'AwsAlbLogs',
            'Effect': 'Allow',
            'Principal': {
                "AWS": "arn:aws:iam::" + elb_region_account_id + ":root"
            },
            'Action': ['s3:PutObject'],
            'Resource': f'arn:aws:s3:::{bucket_name}/*'
        }
        existing_policy["Statement"].append(bucket_policy)

        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(existing_policy))

    def disable_s3_logs(self, arns, s3_bucket):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'false'}]

        for arn in arns:
            response = self.client.describe_load_balancer_attributes(LoadBalancerArn=arn)
            if "Attributes" in response:
                for attribute in response["Attributes"]:
                    if attribute["Key"] == "access_logs.s3.bucket" and attribute["Value"] == s3_bucket:
                        self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)


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

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix, region_account_id):

        bucket_logging = {'LoggingEnabled': {'TargetBucket': s3_bucket, 'TargetPrefix': s3_prefix}}

        if arns:
            for bucket_name in arns:
                if bucket_name != s3_bucket:
                    response = self.client.get_bucket_logging(Bucket=bucket_name)
                    if not ("LoggingEnabled" in response and "TargetBucket" in response["LoggingEnabled"]):
                        try:
                            self.client.put_bucket_logging(Bucket=bucket_name, BucketLoggingStatus=bucket_logging)
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

    def enable_s3_logs(self, arns, s3_bucket, s3_prefix, region_account_id):
        if arns:
            chunk_records = self._batch_size_chunk(arns, 1000)
            for record in chunk_records:
                response = self.client.create_flow_logs(
                    ResourceIds=record,
                    ResourceType='VPC',
                    TrafficType='ALL',
                    LogDestinationType='s3',
                    LogDestination='arn:aws:s3:::' + s3_bucket + '/' + s3_prefix
                )
                if "*Access Denied for LogDestination*" in str(response):
                    self.add_bucket_policy(s3_bucket, s3_prefix)
                    time.sleep(10)
                    self.client.create_flow_logs(
                        ResourceIds=record,
                        ResourceType='VPC',
                        TrafficType='ALL',
                        LogDestinationType='s3',
                        LogDestination='arn:aws:s3:::' + s3_bucket + '/' + s3_prefix
                    )

    def add_bucket_policy(self, bucket_name, prefix):
        print("Adding policy to the bucket " + bucket_name)
        s3 = boto3.client('s3')
        try:
            response = s3.get_bucket_policy(Bucket=bucket_name)
            existing_policy = json.loads(response["Policy"])
        except ClientError as e:
            if "Error" in e.response and "Code" in e.response["Error"] \
                    and e.response['Error']['Code'] == "NoSuchBucketPolicy":
                existing_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                    ]
                }
            else:
                raise e

        bucket_policy = [{
            "Sid": "AWSLogDeliveryAclCheck",
            "Effect": "Allow",
            "Principal": {
                "Service": "delivery.logs.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::" + bucket_name
        },
            {
                "Sid": "AWSLogDeliveryWrite",
                "Effect": "Allow",
                "Principal": {
                    "Service": "delivery.logs.amazonaws.com"
                },
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::" + bucket_name + "/" + prefix + "/AWSLogs/" + self.account_id + "/*",
                "Condition": {
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            }]
        existing_policy["Statement"].extend(bucket_policy)

        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(existing_policy))

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
                    self.client.delete_flow_logs(FlowLogIds=flow_ids)


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
        "CreateVpc": VpcResource
    }

    @classmethod
    def get_provider(cls, provider_name, region_value, account_id, *args, **kwargs):
        if provider_name in cls.provider_map:
            return cls.provider_map[provider_name](provider_name, region_value, account_id)
        else:
            raise Exception("%s provider not found" % provider_name)


if __name__ == '__main__':
    params = {"AWSResource": "s3"}
    # value = ConfigDeliveryChannel()
    # value.create("Six_Hours", "config-bucket-668508221233", "config", "")

    value = EnableS3LogsResources(params)
    # value.create("us-east-2", "s3", "sadasdasdasd-us-east-2", "s3logs/", "", "", "")
    value.delete("us-east-2", "s3", "sadasdasdasd-us-east-2", "s3logs", "", True, "")
