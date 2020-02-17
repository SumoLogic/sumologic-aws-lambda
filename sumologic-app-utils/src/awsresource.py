import importlib
import os
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

    def _tag_aws_resources(self, region_value, aws_resource, tags, account_id, delete_flag):
        # Get the class instance based on AWS Resource
        tag_resource = TagAWSResourcesProvider.get_provider(aws_resource)
        tag_resource.setup(aws_resource, region_value, account_id)

        # Fetch and Filter the Resources.
        resources = tag_resource.fetch_resources()
        filtered_resources = tag_resource.filter_resources([], resources)

        # Get the ARNs for all resources
        arns = tag_resource.get_arn_list(filtered_resources)

        # Tag or un-tag the resources.
        if delete_flag:
            tag_resource.delete_tags(arns, tags)
        else:
            tag_resource.add_tags(arns, tags)

    def create(self, region_value, aws_resource, tags, account_id, *args, **kwargs):
        print("TAG AWS RESOURCES - Starting the AWS resources Tag addition with Tags %s." % tags)
        regions = [region_value]
        for region in regions:
            self._tag_aws_resources(region, aws_resource, tags, account_id, False)
        print("TAG AWS RESOURCES - Completed the AWS resources Tag addition.")

        return {"TAG_CREATION": "Successful"}, "Tag"

    def update(self, region_value, aws_resource, tags, account_id, *args, **kwargs):
        self.create(region_value, aws_resource, tags, account_id, *args, **kwargs)
        print("updated tags for aws resource %s " % aws_resource)
        return {"TAG_UPDATE": "Successful"}, "Tag"

    def delete(self, region_value, aws_resource, tags, account_id, remove_on_delete_stack, *args, **kwargs):
        tags_list = []
        if tags:
            tags_list = list(tags.keys())
        print("TAG AWS RESOURCES - Starting the AWS resources Tag deletion with Tags %s." % tags_list)
        if remove_on_delete_stack:
            regions = [region_value]
            for region in regions:
                self._tag_aws_resources(region, aws_resource, tags, account_id, True)
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
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack")
        }


def resource_tagging(event, context):
    print("AWS RESOURCE TAGGING :- Starting resource tagging")

    # Get Account Id and Alias from env.
    account_alias = os.environ.get("AccountAlias")
    account_id = os.environ.get("AccountID")

    tags = {'account': account_alias}

    if "detail" in event:
        event_detail = event.get("detail")
        event_name = event_detail.get("eventName")
        region_value = event_detail.get("awsRegion")

        # Get the class instance based on Cloudtrail Event Name
        tag_resource = TagAWSResourcesProvider.get_provider(event_name)
        tag_resource.setup(event_name, region_value, account_id)

        # Get the arns from the event.
        resources = tag_resource.get_arn_list_cloud_trail_event(event_detail)

        # Process the existing tags to add some more tags if necessary
        tags = tag_resource.process_tags(tags)

        # Tag the resources
        tag_resource.tag_resources_cloud_trail_event(resources, tags)

    print("AWS RESOURCE TAGGING :- Completed resource tagging")


def enable_s3_logs_alb(event, context):
    print("AWS S3 ENABLE ALB :- Starting s3 logs enable")

    # Get Account Id and Alias from env.
    bucket_name = os.environ.get("BucketName")
    account_id = os.environ.get("AccountID")

    if "detail" in event:
        event_detail = event.get("detail")
        event_name = event_detail.get("eventName")
        region_value = event_detail.get("awsRegion")

        # Get the class instance based on Cloudtrail Event Name
        alb_resource = TagAWSResourcesProvider.get_provider(event_name)
        alb_resource.setup(event_name, region_value, account_id)

        # Get the arns from the event.
        resources = alb_resource.get_arn_list_cloud_trail_event(event_detail)

        # Enable S3 logging
        alb_resource.enable_s3_logs(resources, bucket_name)

    print("AWS S3 ENABLE ALB :- Completed s3 logs enable")


class TagAWSResourcesProvider(object):
    provider_map = {
        "ec2": "awsresource.TagEC2Resources",
        "RunInstances": "awsresource.TagEC2Resources",
        "apigateway": "awsresource.TagApiGatewayResources",
        "CreateStage": "awsresource.TagApiGatewayResources",
        "CreateRestApi": "awsresource.TagApiGatewayResources",
        "CreateDeployment": "awsresource.TagApiGatewayResources",
        "dynamodb": "awsresource.TagDynamoDbResources",
        "CreateTable": "awsresource.TagDynamoDbResources",
        "lambda": "awsresource.TagLambdaResources",
        "CreateFunction20150331": "awsresource.TagLambdaResources",
        "rds": "awsresource.TagRDSResources",
        "CreateDBCluster": "awsresource.TagRDSResources",
        "CreateDBInstance": "awsresource.TagRDSResources",
        "elbv2": "awsresource.TagAlbResources",
        "CreateLoadBalancer": "awsresource.TagAlbResources"
    }

    @classmethod
    def load_class(cls, full_class_string, invoking_module_name):
        """
            dynamically load a class from a string
        """
        try:
            module_path, class_name = cls._split_module_class_name(full_class_string, invoking_module_name)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            raise

    @classmethod
    def _split_module_class_name(cls, full_class_string, invoking_module_name):
        file_name, class_name = full_class_string.rsplit(".", 1)
        parent_module = invoking_module_name.rsplit(".", 1)[0] + "." if "." in invoking_module_name else ""
        full_module_path = f"{parent_module}{file_name}"
        return full_module_path, class_name

    @classmethod
    def get_provider(cls, provider_name, *args, **kwargs):
        if provider_name in cls.provider_map:
            module_class = cls.load_class(cls.provider_map[provider_name], __name__)
            module_instance = module_class(*args, **kwargs)
            return module_instance
        else:
            raise Exception("%s provider not found" % provider_name)


@six.add_metaclass(AutoRegisterResource)
class TagAWSResourcesAbstract(object):
    event_resource_map = {
        "RunInstances": "ec2",
        "CreateStage": "apigateway",
        "CreateRestApi": "apigateway",
        "CreateDeployment": "apigateway",
        "CreateTable": "dynamodb",
        "CreateFunction20150331": "lambda",
        "CreateDBCluster": "rds",
        "CreateDBInstance": "rds",
        "CreateLoadBalancer": "elbv2"
    }

    def setup(self, aws_resource, region_value, account_id):
        self.tagging_client = boto3.client('resourcegroupstaggingapi', region_name=region_value)
        self.client = boto3.client(self.event_resource_map[aws_resource] if aws_resource in self.event_resource_map
                                   else aws_resource, region_name=region_value)
        self.region_value = region_value
        self.account_id = account_id

    @abstractmethod
    def fetch_resources(self):
        raise NotImplementedError()

    @abstractmethod
    def filter_resources(self, *args):
        raise NotImplementedError()

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


class TagEC2Resources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
        return resources

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


class TagApiGatewayResources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
        return resources

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


class TagDynamoDbResources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
        return resources

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


class TagLambdaResources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
        return resources

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


class TagRDSResources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
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


class TagAlbResources(TagAWSResourcesAbstract):

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

    def filter_resources(self, filters, resources):
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

    def enable_s3_logs(self, arns, s3_bucket):
        attributes = [{'Key': 'access_logs.s3.enabled', 'Value': 'true'},
                      {'Key': 'access_logs.s3.bucket', 'Value': s3_bucket}]

        for arn in arns:
            self.client.modify_load_balancer_attributes(LoadBalancerArn=arn, Attributes=attributes)


if __name__ == '__main__':
    params = {}
    tag = TagAWSResources(params)

    tag.create("us-east-1", "elbv2", {'account': 'sdfsdfsd', 'Namespace': "adsas"}, "")

    tag.delete("us-east-1", "elbv2", {'account': 'heelo1', 'Namespace': "adsas"}, "", True)
