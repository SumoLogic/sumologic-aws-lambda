import os
from abc import abstractmethod

import six
import boto3
from botocore.exceptions import ClientError

from resourcefactory import AutoRegisterResource


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

    def _tag_resources_in_group(self, region, resource_arn_list, tags, delete_flag):
        client = boto3.client('resourcegroupstaggingapi', region_name=region)
        if not delete_flag:
            client.tag_resources(ResourceARNList=resource_arn_list, Tags=tags)
        else:
            client.untag_resources(ResourceARNList=resource_arn_list, TagKeys=tags)

    def batch_size_chunk(self, iterable, size=1):
        length = len(iterable)
        for idx in range(0, length, size):
            data = iterable[idx:min(idx + size, length)]
            yield data

    def _tag_aws_resources(self, region, aws_resource, tags, account_id, delete_flag=False):
        client = boto3.client(aws_resource, region_name=region)
        next_token = None
        while next_token != 'END':

            values, next_token = self._call_aws_resource_for_tagging(region, aws_resource, client, next_token,
                                                                     tags, delete_flag, account_id)

            if values:
                print("TAG AWS RESOURCES - %s Resources are %s for region %s" % (aws_resource, values, region))
                chunk_records = self.batch_size_chunk(values, 20)
                for record in chunk_records:
                    self._tag_resources_in_group(region, record, tags, delete_flag)

            if not next_token:
                next_token = 'END'

    def _call_aws_resource_for_tagging(self, region, aws_resource, client, next_token, tags, delete_flag, account_id):
        if aws_resource == 'ec2':
            return self._tag_ec2_resources(region, client, next_token)
        if aws_resource == 'elbv2':
            return self._tag_alb_resources(client, next_token)
        if aws_resource == 'apigateway':
            return self._tag_api_gateway_resources(region, client, next_token)
        if aws_resource == 'lambda':
            return self._tag_lambda_resources(client, next_token)
        if aws_resource == 'rds':
            return self._tag_rds_clusters_resources(region, client, next_token, tags, delete_flag)
        if aws_resource == 'dynamodb':
            return self._tag_dynamodb_resources(region, client, next_token, account_id)

    def _tag_ec2_resources(self, region, client, next_token):
        instances = []
        if next_token:
            response = client.describe_instances(MaxResults=1000, NextToken=next_token)
        else:
            response = client.describe_instances(MaxResults=1000)

        for reservation in response['Reservations']:
            account_id = reservation['OwnerId']
            for ec2_instance in reservation['Instances']:
                instances.append("arn:aws:ec2:" + region + ":" + account_id + ":instance/" + ec2_instance['InstanceId'])

        return instances, response["NextToken"] if "NextToken" in response else None

    def _tag_dynamodb_resources(self, region, client, next_token, account_id):
        tables = []
        if next_token:
            response = client.list_tables(Limit=100, ExclusiveStartTableName=next_token)
        else:
            response = client.list_tables(Limit=100)

        for table_name in response['TableNames']:
            tables.append("arn:aws:dynamodb:" + region + ":" + account_id + ":table/" + table_name)

        return tables, response["LastEvaluatedTableName"] if "LastEvaluatedTableName" in response else None

    def _tag_alb_resources(self, client, next_token):
        albs = []

        if next_token:
            response = client.describe_load_balancers(PageSize=400, Marker=next_token)
        else:
            response = client.describe_load_balancers(PageSize=400)

        for loadBalancer in response['LoadBalancers']:
            albs.append(loadBalancer['LoadBalancerArn'])

        return albs, response["NextMarker"] if "NextMarker" in response else None

    def _tag_api_gateway_resources(self, region, client, next_token):
        api_gateways = []
        if next_token:
            response = client.get_rest_apis(limit=500, position=next_token)
        else:
            response = client.get_rest_apis(limit=500)

        for api in response["items"]:
            id = api["id"]
            api_arn = "arn:aws:apigateway:" + region + "::/restapis/" + id
            api_gateways.append(api_arn)

            stages = client.get_stages(restApiId=id)
            for stage in stages["item"]:
                stage_arn = "arn:aws:apigateway:" + region + "::/restapis/" + id + "/stages/" + stage["stageName"]
                api_gateways.append(stage_arn)

        return api_gateways, response["position"] if "position" in response else None

    def _tag_lambda_resources(self, client, next_token):
        lambdas = []
        if next_token:
            response = client.list_functions(MaxItems=1000, Marker=next_token)
        else:
            response = client.list_functions(MaxItems=1000)

        for function_name in response["Functions"]:
            function_arn = function_name['FunctionArn']
            lambdas.append(function_arn)

        return lambdas, response["NextMarker"] if "NextMarker" in response else None

    def _tag_rds_clusters_resources(self, region, client, next_token, tags, delete_flag):
        if next_token:
            response = client.describe_db_clusters(MaxRecords=100, Marker=next_token)
        else:
            response = client.describe_db_clusters(MaxRecords=100)

        self._tag_rds_resources(region, client, response, "DBClusters", 'DBClusterArn', tags, delete_flag)

        for function_name in response["DBClusters"]:
            cluster_name = function_name['DBClusterIdentifier']
            next_token = None
            filters = [{'Name': 'db-cluster-id', 'Values': [cluster_name]}]
            while next_token != 'END':
                values, next_token = self._tag_rds_instances_resources(region, client, next_token, tags
                                                                       , filters, delete_flag)

                if not next_token:
                    next_token = 'END'

        return None, response["Marker"] if "Marker" in response else None

    def _tag_rds_instances_resources(self, region, client, next_token, tags, filters, delete_flag):
        if next_token:
            response = client.describe_db_instances(MaxRecords=100, Marker=next_token, Filters=filters)
        else:
            response = client.describe_db_instances(MaxRecords=100, Filters=filters)

        self._tag_rds_resources(region, client, response, "DBInstances", 'DBInstanceArn', tags, delete_flag)

        return None, response["Marker"] if "Marker" in response else None

    def _tag_rds_resources(self, region, aws_api, response, root_element, arn_name, tags, delete_flag):
        values = []
        for function_name in response[root_element]:
            function_arn = function_name[arn_name]
            cluster_name = function_name['DBClusterIdentifier']
            values.append(function_arn)
            if not delete_flag:
                aws_api.add_tags_to_resource(ResourceName=function_arn,
                                             Tags=[{'Key': 'account', 'Value': tags.get("account")},
                                                   {'Key': 'cluster', 'Value': cluster_name}])
            else:
                aws_api.remove_tags_from_resource(ResourceName=function_arn, TagKeys=['account', 'cluster'])

        print("TAG AWS RESOURCES - RDS Resources are %s for region %s" % (values, region))

    def create(self, region_value, aws_resource, tags, account_id, *args, **kwargs):
        print("TAG AWS RESOURCES - Starting the AWS resources Tag addition with Tags %s." % tags)
        regions = [region_value]
        for region in regions:
            self._tag_aws_resources(region, aws_resource, tags, account_id)
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
                self._tag_aws_resources(region, aws_resource, tags_list, account_id, True)
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


if __name__ == '__main__':
    tag = TagAWSResources()

    tag.create("us-east-1", "ec2", {'account': 'heelo1', 'Name space': "adsas"}, "")

    tag.delete("us-east-1", "ec2", {'account': 'heelo1', 'Namespace': "adsas"}, "", True)
