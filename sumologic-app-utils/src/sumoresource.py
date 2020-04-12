import json
import re
import tempfile
import time
from abc import abstractmethod
from datetime import datetime

import requests
import six
from resourcefactory import AutoRegisterResource
from sumologic import SumoLogic


@six.add_metaclass(AutoRegisterResource)
class SumoResource(object):

    def __init__(self, props, *args, **kwargs):
        access_id, access_key, deployment = props["SumoAccessID"], props["SumoAccessKey"], props["SumoDeployment"]
        self.deployment = deployment
        self.sumologic_cli = SumoLogic(access_id, access_key, self.api_endpoint)

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

    @property
    def api_endpoint(self):
        if self.deployment == "us1":
            return "https://api.sumologic.com/api"
        elif self.deployment in ["ca", "au", "de", "eu", "jp", "us2", "fed", "in"]:
            return "https://api.%s.sumologic.com/api" % self.deployment
        else:
            return 'https://%s-api.sumologic.net/api' % self.deployment

    def is_enterprise_or_trial_account(self):
        to_time = int(time.time()) * 1000
        from_time = to_time - 5 * 60 * 1000
        try:
            search_query = '''guardduty*
                | "IAMUser" as targetresource
                | "2" as sev
                | "UserPermissions" as threatName
                | "Recon" as threatPurpose
                | benchmark percentage as global_percent from guardduty on threatpurpose=threatPurpose, threatname=threatName, severity=sev, resource=targetresource'''
            response = self.sumologic_cli.search_job(search_query, fromTime=from_time, toTime=to_time)
            print("schedule job status: %s" % response)
            response = self.sumologic_cli.search_job_status(response)
            print("job status: %s" % response)
            if len(response.get("pendingErrors", [])) > 0:
                return False
            else:
                return True
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code == 403:
                return False
            else:
                raise e


class Collector(SumoResource):
    '''
    what happens if property name changes?
    there might be a case in create that it throws duplicate but user properties are not updated so need to call update again?
    Test with updated source category
    Test with existing collector
    '''

    def _get_collector_by_name(self, collector_name, collector_type):
        offset = 0
        page_limit = 300
        all_collectors = self.sumologic_cli.collectors(limit=page_limit, filter_type=collector_type, offset=offset)
        while all_collectors:
            for collector in all_collectors:
                if collector["name"] == collector_name:
                    return collector
            offset += page_limit
            all_collectors = self.sumologic_cli.collectors(limit=page_limit, filter_type=collector_type, offset=offset)

        raise Exception("Collector with name %s not found" % collector_name)

    def create(self, collector_type, collector_name, source_category=None, description='', *args, **kwargs):
        collector_id = None
        collector = {
            'collector': {
                'collectorType': collector_type,
                'name': collector_name,
                'description': description,
                'category': source_category
            }
        }
        try:
            resp = self.sumologic_cli.create_collector(collector, headers=None)
            collector_id = json.loads(resp.text)['collector']['id']
            print("created collector %s" % collector_id)
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()["code"] == 'collectors.validation.name.duplicate':
                collector = self._get_collector_by_name(collector_name, collector_type.lower())
                collector_id = collector['id']
                print("fetched existing collector %s" % collector_id)
            else:
                raise

        return {"COLLECTOR_ID": collector_id}, collector_id

    def update(self, collector_id, collector_type, collector_name, source_category=None, description=None, *args,
               **kwargs):
        cv, etag = self.sumologic_cli.collector(collector_id)
        cv['collector']['category'] = source_category
        cv['collector']['name'] = collector_name
        cv['collector']['description'] = description
        resp = self.sumologic_cli.update_collector(cv, etag)
        collector_id = json.loads(resp.text)['collector']['id']
        print("updated collector %s" % collector_id)
        return {"COLLECTOR_ID": collector_id}, collector_id

    def delete(self, collector_id, remove_on_delete_stack, *args, **kwargs):
        '''
        this should not have any sources?
        '''
        if remove_on_delete_stack:
            sources = self.sumologic_cli.sources(collector_id, limit=10)
            if len(sources) == 0:
                response = self.sumologic_cli.delete_collector({"collector": {"id": collector_id}})
                print("deleted collector %s : %s" % (collector_id, response.text))
        else:
            print("skipping collector deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        collector_id = None
        if event.get('PhysicalResourceId'):
            _, collector_id = event['PhysicalResourceId'].split("/")
        return {
            "collector_type": props.get("CollectorType"),
            "collector_name": props.get("CollectorName"),
            "source_category": props.get("SourceCategory"),
            "description": props.get("Description"),
            "collector_id": collector_id
        }


class Connections(SumoResource):

    def create(self, type, name, description, url, username, password, region, service_name, webhook_type, *args,
               **kwargs):
        connection_id = None
        connection = {
            'type': type,
            'name': name,
            'description': description,
            'headers': [
                {
                    'name': 'accessKey',
                    'value': username
                },
                {
                    'name': 'secretKey',
                    'value': password
                },
                {
                    'name': 'awsRegion',
                    'value': region
                },
                {
                    'name': 'serviceName',
                    'value': service_name
                }
            ],
            'defaultPayload': '{"Types":"HIPAA Controls","Description":"This search","GeneratorID":"InsertFindingsScheduledSearch","Severity":30,"SourceUrl":"https://service.sumologic.com/ui/#/search/RmC8kAUGZbXrkj2rOFmUxmHtzINUgfJnFplh3QWY","ComplianceStatus":"FAILED","Rows":"[{\\"Timeslice\\":1542719060000,\\"finding_time\\":\\"1542719060000\\",\\"item_name\\":\\"A nice dashboard.png\\",\\"title\\":\\"Vulnerability\\",\\"resource_id\\":\\"10.178.11.43\\",\\"resource_type\\":\\"Other\\"}]"}',
            'url': url,
            'webhookType': webhook_type
        }
        try:
            resp = self.sumologic_cli.create_connection(connection, headers=None)
            connection_id = json.loads(resp.text)['id']
            print("created connectionId %s" % connection_id)
        except Exception as e:
            if hasattr(e, 'response'):
                print(e.response.json())
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'connection:name_already_exists':
                        connection_id = e.response.json().get('id')
                        print('Connection already exist', connection_id)
            else:
                raise

        return {"CONNECTION_ID": connection_id}, connection_id

    def update(self, connection_id, type, url, description, username, password, *args, **kwargs):
        cv, etag = self.sumologic_cli.connection(connection_id)
        cv['type'] = type
        cv['url'] = url
        cv['description'] = description
        cv['username'] = username
        cv['password'] = password
        resp = self.sumologic_cli.update_collector(cv, etag)
        connection_id = json.loads(resp.text)['connections']['id']
        print("updated connections %s" % connection_id)
        return {"CONNECTION_ID": connection_id}, connection_id

    def delete(self, connection_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            response = self.sumologic_cli.delete_connection(connection_id, 'WebhookConnection')
            print("deleted connection %s %s" % (connection_id, response.text))
        else:
            print("skipping connection deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        if event.get('PhysicalResourceId'):
            _, connection_id = event['PhysicalResourceId'].split("/")
        return {
            "type": props.get("Type"),
            "name": props.get("Name"),
            "description": props.get("Description"),
            "url": props.get("URL"),
            "username": props.get("UserName"),
            "password": props.get("Password"),
            "region": props.get("Region"),
            "service_name": props.get("ServiceName"),
            "webhook_type": props.get("WebhookType"),
            "id": props.get("ConnectionId"),
            "connection_id": props.get('connection_id')
        }


class BaseSource(SumoResource):

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        source_id = None
        if event.get('PhysicalResourceId'):
            _, source_id = event['PhysicalResourceId'].split("/")
        return {

            "collector_id": props.get("CollectorId"),
            "source_name": props.get("SourceName"),
            "source_id": source_id,
            "props": props
        }

    def build_common_source_params(self, props, source_json=None):
        # https://help.sumologic.com/03Send-Data/Sources/03Use-JSON-to-Configure-Sources#Common_parameters_for_all_Source_types

        source_json = source_json if source_json else {}

        source_json.update({
            "category": props.get("SourceCategory"),
            "name": props.get("SourceName"),
            "description": "This %s source is created by AWS SAM Application" % (props.get("SourceType", "HTTP"))
        })
        # timestamp processing
        if props.get("DateFormat"):
            source_json["defaultDateFormats"] = [{"format": props.get("DateFormat"), "locator": props.get("DateLocatorRegex")}]

        # processing rules
        if 'filters' in props and isinstance(props['filters'], list):
            filters = [x for x in props['filters'] if x['regexp'].strip()]
            if filters:
                source_json['filters'] = filters

        # Fields condition
        if 'Fields' in props:
            source_json['fields'] = props.get("Fields")

        # multi line processing
        if 'multilineProcessingEnabled' in props:
            source_json['multilineProcessingEnabled'] = props['multilineProcessingEnabled']
        if 'useAutolineMatching' in props:
            source_json['useAutolineMatching'] = props['useAutolineMatching']

        return source_json


class AWSSource(BaseSource):

    def build_source_params(self, props, source_json = None):
        # https://help.sumologic.com/03Send-Data/Sources/03Use-JSON-to-Configure-Sources/JSON-Parameters-for-Hosted-Sources#aws-log-sources

        source_json = source_json if source_json else {}
        source_json = self.build_common_source_params(props, source_json)
        source_json.update({
            "sourceType": "Polling",
            "contentType": props.get("SourceType"),
            "thirdPartyRef": {
                "resources": [{
                    "serviceType": props.get("SourceType"),
                    "path": self._get_path(props),
                    "authentication": {
                        "type": "AWSRoleBasedAuthentication",
                        "roleARN": props.get("RoleArn")
                    }
                }]
            },
            "scanInterval": 300000,
            "paused": False,
        })
        return source_json

    def _get_path(self, props):
        source_type = props.get("SourceType")

        regions = []
        if "Region" in props:
            regions = [props.get("Region")]

        if source_type == "AwsMetadata":
            return {
                "type": "AwsMetadataPath",
                "limitToRegions": regions
            }
        elif source_type == "AwsCloudWatch":
            return {
                "type": "CloudWatchPath",
                "limitToRegions": regions,
                "limitToNamespaces": props.get("Namespaces")
            }
        elif source_type == "AwsInventory":
            return {
                "type": "AwsInventoryPath",
                "limitToRegions": regions,
                "limitToNamespaces": props.get("Namespaces")
            }
        else:
            return {
                "type": "S3BucketPathExpression",
                "bucketName": props.get("TargetBucketName"),
                "pathExpression": props.get("PathExpression")
            }

    def create(self, collector_id, source_name, props, *args, **kwargs):

        endpoint = source_id = None
        source_json = {"source": self.build_source_params(props)}
        try:
            resp = self.sumologic_cli.create_source(collector_id, source_json)
            data = resp.json()['source']
            source_id = data["id"]
            endpoint = data["url"]
            print("created source %s" % source_id)
        except Exception as e:
            # Todo 100 sources in a collector is good. Same error code for duplicates in case of Collector and source.
            if hasattr(e, 'response') and e.response.json()["code"] == 'collectors.validation.name.duplicate':
                for source in self.sumologic_cli.sources(collector_id, limit=300):
                    if source["name"] == source_name:
                        source_id = source["id"]
                        print("fetched existing source %s" % source_id)
                        endpoint = source["url"]
            else:
                print(e, source_json)
                raise
        return {"SUMO_ENDPOINT": endpoint}, source_id

    def update(self, collector_id, source_id, source_name, props, *args,
               **kwargs):
        source_json, etag = self.sumologic_cli.source(collector_id, source_id)
        source_json['source'] = self.build_source_params(props, source_json['source'])
        try:
            resp = self.sumologic_cli.update_source(collector_id, source_json, etag)
            data = resp.json()['source']
            print("updated source %s" % data["id"])
            return {"SUMO_ENDPOINT": data["url"]}, data["id"]
        except Exception as e:
            print(e, source_json)
            raise

    def delete(self, collector_id, source_id, remove_on_delete_stack, props, *args, **kwargs):
        if remove_on_delete_stack:
            response = self.sumologic_cli.delete_source(collector_id, {"source": {"id": source_id}})
            print("deleted source %s : %s" % (source_id, response.text))
        else:
            print("skipping source deletion")


class HTTPSource(SumoResource):
    # Todo refactor this to use basesource class

    def create(self, collector_id, source_name, source_category, fields, message_per_request,
               date_format=None, date_locator="\"timestamp\": (.*),", *args, **kwargs):

        endpoint = source_id = None
        params = {
            "sourceType": "HTTP",
            "name": source_name,
            "messagePerRequest": message_per_request,
            "multilineProcessingEnabled": False if message_per_request else True,
            "category": source_category
        }
        if date_format:
            params["defaultDateFormats"] = [{"format": date_format, "locator": date_locator}]

        # Fields condition
        if fields:
            params['fields'] = fields

        try:
            resp = self.sumologic_cli.create_source(collector_id, {"source": params})
            data = resp.json()['source']
            source_id = data["id"]
            endpoint = data["url"]
            print("created source %s" % source_id)
        except Exception as e:
            # Todo 100 sources in a collector is good
            if hasattr(e, 'response') and e.response.json()["code"] == 'collectors.validation.name.duplicate':
                for source in self.sumologic_cli.sources(collector_id, limit=300):
                    if source["name"] == source_name:
                        source_id = source["id"]
                        print("fetched existing source %s" % source_id)
                        endpoint = source["url"]
            else:
                raise
        return {"SUMO_ENDPOINT": endpoint}, source_id

    def update(self, collector_id, source_id, source_name, source_category, date_format=None, date_locator=None, *args,
               **kwargs):
        sv, etag = self.sumologic_cli.source(collector_id, source_id)
        sv['source']['category'] = source_category
        sv['source']['name'] = source_name
        if date_format:
            sv['source']["defaultDateFormats"] = [{"format": date_format, "locator": date_locator}]
        resp = self.sumologic_cli.update_source(collector_id, sv, etag)
        data = resp.json()['source']
        print("updated source %s" % data["id"])
        return {"SUMO_ENDPOINT": data["url"]}, data["id"]

    def delete(self, collector_id, source_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            response = self.sumologic_cli.delete_source(collector_id, {"source": {"id": source_id}})
            print("deleted source %s : %s" % (source_id, response.text))
        else:
            print("skipping source deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        source_id = None
        if event.get('PhysicalResourceId'):
            _, source_id = event['PhysicalResourceId'].split("/")

        fields = {}
        if 'Fields' in props:
            fields = props.get("Fields")

        return {
            "collector_id": props.get("CollectorId"),
            "source_name": props.get("SourceName"),
            "source_category": props.get("SourceCategory"),
            "date_format": props.get("DateFormat"),
            "date_locator": props.get("DateLocatorRegex"),
            "message_per_request": props.get("MessagePerRequest") == 'true',
            "source_id": source_id,
            "fields": fields
        }


class App(SumoResource):

    ENTERPRISE_ONLY_APPS = {"Amazon GuardDuty Benchmark", "Global Intelligence for AWS CloudTrail"}

    def _convert_to_hour(self, timeoffset):
        hour = timeoffset / 60 * 60 * 1000
        return "%sh" % (hour)

    def _replace_source_category(self, appjson_filepath, sourceDict):
        with open(appjson_filepath, 'r') as old_file:
            text = old_file.read()
            for k, v in sourceDict.items():
                text = text.replace("$$%s" % k, v)
            appjson = json.loads(text)

        return appjson

    def _add_time_suffix(self, appjson):
        date_format = "%Y-%m-%d %H:%M:%S"
        appjson['name'] = appjson['name'] + "-" + datetime.utcnow().strftime(date_format)
        return appjson

    def _get_app_folder(self, appdata, parent_id):
        folder_id = None
        try:
            response = self.sumologic_cli.create_folder(appdata["name"], appdata["description"][:255], parent_id)
            folder_id = response.json()["id"]
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()['errors']:
                msg = e.response.json()['errors'][0]['message']
                matched = re.search('(?<=ContentId\()\d+', msg)
                if matched:
                    folder_id = matched[0]
            else:
                raise
        return folder_id

    def _get_app_content(self, appname, source_params):
        key_name = "ApiExported-" + re.sub(r"\s+", "-", appname) + ".json"
        s3url = "https://app-json-store.s3.amazonaws.com/%s" % key_name
        print("Fetching appjson %s" % s3url)
        with requests.get(s3url, stream=True) as r:
            r.raise_for_status()
            with tempfile.NamedTemporaryFile() as fp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fp.write(chunk)
                fp.flush()
                fp.seek(0)
                appjson = self._replace_source_category(fp.name, source_params)
                appjson = self._add_time_suffix(appjson)

        return appjson

    def _wait_for_folder_creation(self, folder_id, job_id):
        print("waiting for folder creation folder_id %s job_id %s" % (folder_id, job_id))
        waiting = True
        while waiting:
            response = self.sumologic_cli.check_import_status(folder_id, job_id)
            waiting = response.json()['status'] == "InProgress"
            time.sleep(5)

        print("job status: %s" % response.text)

    def _wait_for_app_install(self, job_id):
        print("waiting for app installation job_id %s" % job_id)
        waiting = True
        while waiting:
            response = self.sumologic_cli.check_app_install_status(job_id)
            waiting = response.json()['status'] == "InProgress"
            time.sleep(5)
        print("job status: %s" % response.text)
        return response

    def _create_or_fetch_quickstart_apps_parent_folder(self, folder_prefix):
        response = self.sumologic_cli.get_personal_folder()
        folder_name = folder_prefix + str(datetime.now().strftime("%d-%m-%Y"))
        description = "This folder contains all the apps created as a part of SumoLogic Amazon QuickStart Apps."
        try:
            folder = self.sumologic_cli.create_folder(folder_name, description, response.json()['id'])
            return folder.json()["id"]
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'content:duplicate_content':
                        if "children" in response.json():
                            for children in response.json()["children"]:
                                if "name" in children and children["name"] == folder_name:
                                    return children["id"]
            else:
                raise

    def create_by_import_api(self, appname, source_params, *args, **kwargs):
        # Add  retry if folder sync fails
        if appname in self.ENTERPRISE_ONLY_APPS and not self.is_enterprise_or_trial_account():
            raise Exception("%s is available to Enterprise or Trial Account Type only." % appname)

        content = self._get_app_content(appname, source_params)

        if "AWS Observability" in appname:
            folder_id = self._create_or_fetch_quickstart_apps_parent_folder("Sumo Logic AWS Observability Apps ")
        else:
            response = self.sumologic_cli.get_personal_folder()
            folder_id = response.json()['id']
        app_folder_id = self._get_app_folder(content, folder_id)
        response = self.sumologic_cli.import_content(folder_id, content, is_overwrite="true")
        job_id = response.json()["id"]
        print("installed app %s: appFolderId: %s personalFolderId: %s jobId: %s" % (
            appname, app_folder_id, folder_id, job_id))
        self._wait_for_folder_creation(folder_id, job_id)
        return {"APP_FOLDER_NAME": content["name"]}, app_folder_id

    def create_by_install_api(self, appid, appname, source_params, *args, **kwargs):
        if appname in self.ENTERPRISE_ONLY_APPS and not self.is_enterprise_or_trial_account():
            raise Exception("%s is available to Enterprise or Trial Account Type only." % appname)

        if "Amazon QuickStart" in appname:
            folder_id = self._create_or_fetch_quickstart_apps_parent_folder("SumoLogic Amazon QuickStart Apps ")
        else:
            response = self.sumologic_cli.get_personal_folder()
            folder_id = response.json()['id']
        content = {'name': appname + datetime.now().strftime("_%d-%b-%Y_%H:%M:%S.%f"), 'description': appname,
                   'dataSourceValues': source_params, 'destinationFolderId': folder_id}

        response = self.sumologic_cli.install_app(appid, content)
        job_id = response.json()["id"]
        response = self._wait_for_app_install(job_id)

        json_resp = json.loads(response.content)
        if (json_resp['status'] == 'Success'):
            app_folder_id = json_resp['statusMessage'].split(":")[1]
            print("installed app %s: appFolderId: %s parent_folder_id: %s jobId: %s" % (
                appname, app_folder_id, folder_id, job_id))
            return {"APP_FOLDER_NAME": content["name"]}, app_folder_id
        else:
            print("%s installation failed." % appname)
            response.raise_for_status()

    def create(self, appname, source_params, appid=None, *args, **kwargs):
        if appid:
            return self.create_by_install_api(appid, appname, source_params, *args, **kwargs)
        else:
            return self.create_by_import_api(appname, source_params, *args, **kwargs)


    def update(self, app_folder_id, appname, source_params, appid=None, *args, **kwargs):
        self.delete(app_folder_id, remove_on_delete_stack=True)
        data, app_folder_id = self.create(appname, source_params, appid)
        print("updated app appFolderId: %s " % app_folder_id)
        return data, app_folder_id

    def delete(self, app_folder_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            response = self.sumologic_cli.delete_folder(app_folder_id)
            print("deleting app folder %s : %s" % (app_folder_id, response.text))
        else:
            print("skipping app folder deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        app_folder_id = None
        if event.get('PhysicalResourceId'):
            _, app_folder_id = event['PhysicalResourceId'].split("/")
        return {
            "appid": props.get("AppId"),
            "appname": props.get("AppName"),
            "source_params": props.get("AppSources"),
            "app_folder_id": app_folder_id
        }


class SumoLogicAWSExplorer(SumoResource):
    def create(self, explorer_name, hierarchy, *args, **kwargs):
        content = {
            "name": explorer_name,
            "baseFilter": [],
            "hierarchy": hierarchy
        }
        try:
            response = self.sumologic_cli.create_explorer_view(content)
            job_id = response.json()["id"]
            print("AWS EXPLORER -  creation successful with ID %s" % job_id)
            return {"EXPLORER_NAME": response.json()["name"]}, job_id
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'topology:duplicate':
                        print("AWS EXPLORER -  Duplicate Exists for Name %s" % explorer_name)
                        return {"EXPLORER_NAME": explorer_name}, "Duplicate"
            raise e

    # No Update API. So, Explorer view can be updated and deleted from the main stack where it was created.
    def update(self, explorer_id, explorer_name, hierarchy, *args, **kwargs):
        self.delete(explorer_id, explorer_name, hierarchy, True, *args, **kwargs)
        data, explorer_id = self.create(explorer_name, hierarchy, *args, **kwargs)
        return data, explorer_id

    def delete(self, explorer_id, explorer_name, hierarchy, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack and explorer_id != "Duplicate":
            response = self.sumologic_cli.delete_explorer_view(explorer_id)
            print("AWS EXPLORER - Completed the AWS Explorer deletion for Name %s, response - %s" % (
                explorer_name, response.text))
        else:
            print("AWS EXPLORER - Skipping the AWS Explorer deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        explorer_id = None
        if event.get('PhysicalResourceId'):
            _, explorer_id = event['PhysicalResourceId'].split("/")

        hierarchy = []
        if "MetadataKeys" in props:
            metadata_keys = props.get("MetadataKeys")
            for value in metadata_keys:
                hierarchy.append({"metadataKey": value})

        return {
            "explorer_name": props.get("ExplorerName"),
            "explorer_id": explorer_id,
            "hierarchy": hierarchy
        }


class SumoLogicMetricRules(SumoResource):
    def create(self, metric_rule_name, match_expression, variables, *args, **kwargs):

        variables_to_extract = []
        if variables:
            for k, v in variables.items():
                variables_to_extract.append({"name": k, "tagSequence": v})

        content = {
            "name": metric_rule_name,
            "matchExpression": match_expression,
            "variablesToExtract": variables_to_extract
        }
        try:
            response = self.sumologic_cli.create_metric_rule(content)
            job_name = response.json()["name"]
            print("METRIC RULES -  creation successful with Name %s" % job_name)
            return {"METRIC_RULES": response.json()["name"]}, job_name
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'metrics:rule_name_already_exists' \
                            or error.get('code') == 'metrics:rule_already_exists':
                        print("METRIC RULES -  Duplicate Exists for Name %s" % metric_rule_name)
                        return {"METRIC_RULES": metric_rule_name}, "Duplicate"
            raise e

    # No Update API. So, Metric rules can be updated and deleted from the main stack where it was created.
    def update(self, job_name, metric_rule_name, match_expression, variables, *args, **kwargs):
        self.delete(job_name, metric_rule_name, True, *args, **kwargs)
        data, job_name = self.create(metric_rule_name, match_expression, variables, *args, **kwargs)
        return data, job_name

    def delete(self, job_name, metric_rule_name, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack and job_name != "Duplicate":
            response = self.sumologic_cli.delete_metric_rule(job_name)
            print("METRIC RULES - Completed the Metric Rule deletion for Name %s, response - %s" % (
                job_name, response.text))
        else:
            print("METRIC RULES - Skipping the Metric Rule deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        job_name = None
        if event.get('PhysicalResourceId'):
            _, job_name = event['PhysicalResourceId'].split("/")

        variables = {}
        if "ExtractVariables" in props:
            variables = props.get("ExtractVariables")

        return {
            "metric_rule_name": props.get("MetricRuleName"),
            "match_expression": props.get("MatchExpression"),
            "variables": variables,
            "job_name": job_name
        }


class SumoLogicUpdateFields(SumoResource):

    def create(self, collector_id, source_name, fields, *args, **kwargs):
        if collector_id:
            sources = self.sumologic_cli.sources(collector_id, limit=300)
            source_id = None
            for source in sources:
                if source["name"] == source_name:
                    source_id = source["id"]

            sv, etag = self.sumologic_cli.source(collector_id, source_id)

            existing_fields = sv['source']['fields']

            new_fields = existing_fields.copy()
            new_fields.update(fields)

            sv['source']['fields'] = new_fields

            resp = self.sumologic_cli.update_source(collector_id, sv, etag)

            data = resp.json()['source']
            print("updated Fields in Source %s" % data["id"])

            return {"existing_fields": existing_fields}, source_id
        return {"existing_fields": "Not updated"}, "No Id"

    # Update the new fields to source.
    def update(self, collector_id, source_name, fields, *args, **kwargs):
        data, source_id = self.create(collector_id, source_name, fields, *args, **kwargs)
        return data, source_id

    def delete(self, collector_id, source_id, fields, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            sv, etag = self.sumologic_cli.source(collector_id, source_id)
            existing_fields = sv['source']['fields']

            for k in fields:
                existing_fields.pop(k, None)

            sv['source']['fields'] = existing_fields
            resp = self.sumologic_cli.update_source(collector_id, sv, etag)

            data = resp.json()['source']
            print("reverted Fields in Source %s" % data["id"])
        else:
            print("UPDATE FIELDS - Skipping the Metric Rule deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        source_id = None
        if event.get('PhysicalResourceId'):
            _, source_id = event['PhysicalResourceId'].split("/")

        fields = {}
        if "Fields" in props:
            fields = props.get("Fields")

        return {
            "collector_id": props.get("CollectorId"),
            "source_name": props.get("SourceName"),
            "fields": fields,
            "source_id": source_id
        }


class SumoLogicFieldExtractionRule(SumoResource):
    def _get_fer_by_name(self, fer_name):
        token = ""
        page_limit = 100
        response = self.sumologic_cli.get_all_field_extraction_rules(limit=page_limit, token=token)
        while response:
            print("calling FER API with token "+ token)
            for fer in response['data']:
                if fer["name"] == fer_name:
                    return fer
            token = response['next']
            if token:
                response = self.sumologic_cli.get_all_field_extraction_rules(limit=page_limit, token=token)
            else:
                response = None

        raise Exception("FER with name %s not found" % fer_name)

    def create(self, fer_name, fer_scope, fer_expression, fer_enabled, *args, **kwargs):
        content = {
            "name": fer_name,
            "scope": fer_scope,
            "parseExpression": fer_expression,
            "enabled": fer_enabled
        }
        try:
            response = self.sumologic_cli.create_field_extraction_rule(content)
            job_id = response.json()["id"]
            print("FER RULES -  creation successful with ID %s" % job_id)
            return {"FER_RULES": response.json()["name"]}, job_id
        except Exception as e:
            if hasattr(e, 'response') and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'fer:invalid_extraction_rule':
                        print("FER RULES -  Duplicate Exists for Name %s" % fer_name)
                        # check if there is difference in scope, if yes then merge the scopes.
                        fer_details = self._get_fer_by_name(fer_name)
                        if "scope" in fer_details and fer_scope not in fer_details["scope"]:
                            fer_details["scope"] = fer_details["scope"] + " or " + fer_scope
                            self.sumologic_cli.update_field_extraction_rules(fer_details["id"], fer_details)
                        return {"FER_RULES": fer_name}, "Duplicate"
            raise e

    # Field Extraction Rule can be updated and deleted from the main stack where it was created.
    def update(self, fer_id, fer_name, fer_scope, fer_expression, fer_enabled, *args, **kwargs):
        data, fer_id = self.create(fer_name, fer_scope, fer_expression, fer_enabled, *args, **kwargs)
        return data, fer_id

    def delete(self, fer_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack and fer_id != "Duplicate":
            response = self.sumologic_cli.delete_field_extraction_rule(fer_id)
            print("FER RULES - Completed the Metric Rule deletion for ID %s, response - %s" % (
                fer_id, response.text))
        else:
            print("FER RULES - Skipping the Metric Rule deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        fer_id = None
        if event.get('PhysicalResourceId'):
            _, fer_id = event['PhysicalResourceId'].split("/")

        return {
            "fer_name": props.get("FieldExtractionRuleName"),
            "fer_scope": props.get("FieldExtractionRuleScope"),
            "fer_expression": props.get("FieldExtractionRuleParseExpression"),
            "fer_enabled": props.get("FieldExtractionRuleParseEnabled"),
            "fer_id": fer_id
        }


if __name__ == '__main__':

    props = {
        "SumoAccessID": "",
        "SumoAccessKey": "",
        "SumoDeployment": "us1",
    }
    app_prefix = "CloudTrail"
    # app_prefix = "GuardDuty"
    collector_id = None
    collector_type = "Hosted"
    collector_name = "%sCollector" % app_prefix
    source_name = "%sEvents" % app_prefix
    source_category = "Labs/AWS/%s" % app_prefix
    # appname = "Global Intelligence for Amazon GuardDuty"
    appname = "Global Intelligence for AWS CloudTrail"
    appid = "570bdc0d-f824-4fcb-96b2-3230d4497180"
    # appid = "ceb7fac5-1137-4a04-a5b8-2e49190be3d4"
    # appid = None
    # source_params = {
    #     "logsrc": "_sourceCategory=%s" % source_category
    # }
    source_params = {
        "cloudtraillogsource": "_sourceCategory=%s" % source_category,
        "indexname": '%rnd%',
        "incrementalindex": "%rnd%"
    }
    # col = Collector(**params)
    # src = HTTPSource(**params)
    app = App(props)

    # create
    # _, collector_id = col.create(collector_type, collector_name, source_category)
    # _, source_id = src.create(collector_id, source_name, source_category)

    _, app_folder_id = app.create(appname, source_params, appid)
    app.delete(app_folder_id, True)

    # update
    # _, new_collector_id = col.update(collector_id, collector_type, "%sCollectorNew" % app_prefix, "Labs/AWS/%sNew" % app_prefix, description="%s Collector" % app_prefix)
    # assert(collector_id == new_collector_id)
    # _, new_source_id = src.update(collector_id, source_id, "%sEventsNew" % app_prefix, "Labs/AWS/%sNew" % app_prefix, date_format="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", date_locator='\"createTime\":(.*),')
    # assert(source_id == new_source_id)
    # new_source_params = {
    #     "logsrc": "_sourceCategory=%s" % ("Labs/AWS/%sNew" % app_prefix)
    # }

    # _, new_app_folder_id = app.update(app_folder_id, appname, new_source_params, appid)
    # assert(app_folder_id != new_app_folder_id)

    # delete
    # src.delete(collector_id, source_id, True)
    # col.delete(collector_id, True)
    # app.delete(new_app_folder_id, True)

