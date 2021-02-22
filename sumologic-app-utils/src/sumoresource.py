import json
import re
import tempfile
import time
from abc import abstractmethod
from datetime import datetime
from random import uniform

import requests
import six
from resourcefactory import AutoRegisterResource
from sumologic import SumoLogic
from awsresource import AWSResourcesProvider


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
                | toint(sev) as sev
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
            if hasattr(e, 'response') and "code" in e.response.json() and e.response.json()["code"] == 'collectors.validation.name.duplicate':
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

        # Adding Cutofftimestamp 24 hours.
        source_json['cutoffTimestamp'] = int(round(time.time() * 1000)) - 24 * 60 * 60 * 1000

        return source_json


class AWSSource(BaseSource):

    def build_source_params(self, props, source_json=None):
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
            "scanInterval": int(props.get("ScanInterval")) if "ScanInterval" in props else 300000,
            "paused": False,
        })
        return source_json

    def _get_path(self, props):
        source_type = props.get("SourceType")

        regions = []
        if "Region" in props:
            regions = [props.get("Region")]

        if props.get("TargetBucketName"):
            return {
                "type": "S3BucketPathExpression",
                "bucketName": props.get("TargetBucketName"),
                "pathExpression": props.get("PathExpression")
            }
        else:
            path = {}
            if regions:
                path["limitToRegions"] = regions
            if "Namespaces" in props:
                path["limitToNamespaces"] = props.get("Namespaces")
            if source_type == "AwsCloudWatch":
                path["type"] = "CloudWatchPath"
            else:
                path["type"] = source_type + "Path"
            return path

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
            if hasattr(e, 'response') and "code" in e.response.json() and e.response.json()["code"] == 'collectors.validation.name.duplicate':
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


class HTTPSource(BaseSource):

    def build_source_params(self, props, source_json=None):

        source_json = self.build_common_source_params(props, source_json)

        source_json["messagePerRequest"] = props.get("MessagePerRequest") == 'true'
        source_json["multilineProcessingEnabled"] = False if source_json["messagePerRequest"] else True
        source_json["sourceType"] = "HTTP"

        if props.get("SourceType"):
            source_json.update({
                "contentType": props.get("SourceType"),
                "thirdPartyRef": {
                    "resources": [{
                        "serviceType": props.get("SourceType"),
                        "path": {
                            "type": props.get("SourceType") + "Path",
                        },
                        "authentication": {
                            "type": "AWSRoleBasedAuthentication",
                            "roleARN": props.get("RoleArn")
                        }
                    }]
                }
            })
        return source_json

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
            # Todo 100 sources in a collector is good
            if hasattr(e, 'response') and "code" in e.response.json() and e.response.json()["code"] == 'collectors.validation.name.duplicate':
                for source in self.sumologic_cli.sources(collector_id, limit=300):
                    if source["name"] == source_name:
                        source_id = source["id"]
                        print("fetched existing source %s" % source_id)
                        endpoint = source["url"]
            else:
                raise
        return {"SUMO_ENDPOINT": endpoint}, source_id

    def update(self, collector_id, source_id, source_name, props, *args,
               **kwargs):
        sv, etag = self.sumologic_cli.source(collector_id, source_id)
        sv['source'] = self.build_source_params(props, sv['source'])

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

        return {
            "collector_id": props.get("CollectorId"),
            "source_name": props.get("SourceName"),
            "source_id": source_id,
            "props": props,
        }


class App(SumoResource):

    ENTERPRISE_ONLY_APPS = {"Amazon GuardDuty Benchmark", "Global Intelligence for AWS CloudTrail"}

    def _convert_to_hour(self, timeoffset):
        hour = timeoffset / 60 * 60 * 1000
        return "%sh" % (hour)

    def _replace_source_category(self, appjson_filepath, sourceDict):
        with open(appjson_filepath, 'r') as old_file:
            text = old_file.read()
            if sourceDict:
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
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'content:duplicate_content':
                        folder_details = self.sumologic_cli.get_folder_by_id(parent_id)
                        if "children" in folder_details:
                            for children in folder_details["children"]:
                                if "name" in children and children["name"] == appdata["name"]:
                                    return children["id"]
                raise
        return folder_id

    def _get_app_content(self, appname, source_params, s3url=None):
        # Based on S3 URL provided download the data.
        if not s3url:
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

    def _wait_for_folder_copy(self, folder_id, job_id):
        print("waiting for folder copy folder_id %s job_id %s" % (folder_id, job_id))
        waiting = True
        while waiting:
            response = self.sumologic_cli.check_copy_status(folder_id, job_id)
            waiting = response.json()['status'] == "InProgress"
            time.sleep(5)

        print("job status: %s" % response.text)
        matched = re.search('id:\s*(.*?)\"', response.text)
        copied_folder_id = None
        if matched:
            copied_folder_id = matched[1]
        return copied_folder_id

    def _wait_for_app_install(self, job_id):
        print("waiting for app installation job_id %s" % job_id)
        waiting = True
        while waiting:
            response = self.sumologic_cli.check_app_install_status(job_id)
            waiting = response.json()['status'] == "InProgress"
            time.sleep(5)
        print("job status: %s" % response.text)
        return response

    def _create_backup_folder(self, new_app_folder_id, old_app_folder_id):
        new_folder_details = self.sumologic_cli.get_folder_by_id(new_app_folder_id)
        parent_folder_id = new_folder_details["parentId"]

        old_folder_details = self.sumologic_cli.get_folder_by_id(old_app_folder_id)
        old_parent_folder_details = self.sumologic_cli.get_folder_by_id(old_folder_details["parentId"])

        if old_parent_folder_details.get("parentId") == "0000000000000000":
            back_up = "Back Up Old App"
        else:
            back_up = "Back Up " + old_parent_folder_details["name"]

        backup_folder_id = self._get_app_folder({"name": back_up,
                                                 "description": "The folder contains back up of all the apps that are updated using CloudFormation template."},
                                                parent_folder_id)
        return backup_folder_id

    def _create_or_fetch_apps_parent_folder(self, folder_prefix):
        response = self.sumologic_cli.get_personal_folder()
        folder_name = folder_prefix + str(datetime.now().strftime(" %d-%b-%Y"))
        description = "This folder contains all the apps created as a part of Sumo Logic Solutions."
        try:
            folder = self.sumologic_cli.create_folder(folder_name, description, response.json()['id'])
            return folder.json()["id"]
        except Exception as e:
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'content:duplicate_content':
                        response = self.sumologic_cli.get_personal_folder()
                        if "children" in response.json():
                            for children in response.json()["children"]:
                                if "name" in children and children["name"] == folder_name:
                                    return children["id"]
            raise

    def create_by_import_api(self, appname, source_params, folder_name, s3url, *args, **kwargs):
        # Add  retry if folder sync fails
        if appname in self.ENTERPRISE_ONLY_APPS and not self.is_enterprise_or_trial_account():
            raise Exception("%s is available to Enterprise or Trial Account Type only." % appname)

        content = self._get_app_content(appname, source_params, s3url)

        if folder_name:
            folder_id = self._create_or_fetch_apps_parent_folder(folder_name)
        else:
            response = self.sumologic_cli.get_personal_folder()
            folder_id = response.json()['id']
        app_folder_id = self._get_app_folder(content, folder_id)
        time.sleep(5)
        response = self.sumologic_cli.import_content(folder_id, content, is_overwrite="true")
        job_id = response.json()["id"]
        print("installed app %s: appFolderId: %s personalFolderId: %s jobId: %s" % (
            appname, app_folder_id, folder_id, job_id))
        self._wait_for_folder_creation(folder_id, job_id)
        return {"APP_FOLDER_NAME": content["name"]}, app_folder_id

    def create_by_install_api(self, appid, appname, source_params, folder_name, *args, **kwargs):
        if appname in self.ENTERPRISE_ONLY_APPS and not self.is_enterprise_or_trial_account():
            raise Exception("%s is available to Enterprise or Trial Account Type only." % appname)

        folder_id = None

        if folder_name:
            folder_id = self._create_or_fetch_apps_parent_folder(folder_name)
        else:
            response = self.sumologic_cli.get_personal_folder()
            folder_id = response.json()['id']

        content = {'name': appname + datetime.now().strftime(" %d-%b-%Y %H:%M:%S"), 'description': appname,
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
            raise Exception(response.text)

    def create(self, appname, source_params, appid=None, folder_name=None, s3url=None, *args, **kwargs):
        if appid:
            return self.create_by_install_api(appid, appname, source_params, folder_name, *args, **kwargs)
        else:
            return self.create_by_import_api(appname, source_params, folder_name, s3url, *args, **kwargs)

    def update(self, app_folder_id, appname, source_params, appid=None, folder_name=None, retain_old_app=False,
               s3url=None, *args, **kwargs):
        # Delete is called by CF itself on Old Resource if we create a new resource. So, no need to delete the resource here.
        # self.delete(app_folder_id, remove_on_delete_stack=True)
        data, new_app_folder_id = self.create(appname, source_params, appid, folder_name, s3url)
        print("updated app appFolderId: %s " % new_app_folder_id)
        if retain_old_app:
            backup_folder_id = self._create_backup_folder(new_app_folder_id, app_folder_id)
            # Starting Folder Copy
            response = self.sumologic_cli.copy_folder(app_folder_id, backup_folder_id)
            job_id = response.json()["id"]
            print("Copy Completed parentFolderId: %s jobId: %s" % (backup_folder_id, job_id))
            copied_folder_id = self._wait_for_folder_copy(app_folder_id, job_id)
            # Updating copied folder name with suffix BackUp.
            copied_folder_details = self.sumologic_cli.get_folder_by_id(copied_folder_id)
            copied_folder_details = {"name": copied_folder_details["name"].replace("(Copy)", "- BackUp_" + datetime.now().strftime("%H:%M:%S")),
                                     "description": copied_folder_details["description"][:255]}
            self.sumologic_cli.update_folder_by_id(copied_folder_id, copied_folder_details)
            print("Back Up done for the APP: %s." % backup_folder_id)
        return data, new_app_folder_id

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
            "folder_name": props.get("FolderName"),
            "retain_old_app": props.get("RetainOldAppOnUpdate") == 'true',
            "app_folder_id": app_folder_id,
            "s3url": props.get("AppJsonS3Url")
        }


class SumoLogicAWSExplorer(SumoResource):

    def get_explorer_id(self, hierarchy_name):
        hierarchies = self.sumologic_cli.get_entity_hierarchies()
        if hierarchies and "data" in hierarchies:
            for hierarchy in hierarchies["data"]:
                if hierarchy_name == hierarchy["name"]:
                    return hierarchy["id"]
        raise Exception("Hierarchy with name %s not found" % hierarchy_name)

    def create_hierarchy(self, hierarchy_name, level, hierarchy_filter):
        content = {
            "name": hierarchy_name,
            "filter": hierarchy_filter,
            "level": level
        }
        try:
            response = self.sumologic_cli.create_hierarchy(content)
            hierarchy_id = response.json()["id"]
            print("Hierarchy -  creation successful with ID %s" % hierarchy_id)
            return {"Hierarchy_Name": response.json()["name"]}, hierarchy_id
        except Exception as e:
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'hierarchy:duplicate':
                        print("Hierarchy -  Duplicate Exists for Name %s" % hierarchy_name)
                        # Get the hierarchy ID from all explorer.
                        hierarchy_id = self.get_explorer_id(hierarchy_name)
                        response = self.sumologic_cli.update_hierarchy(hierarchy_id, content)
                        hierarchy_id = response.json()["id"]
                        print("Hierarchy -  update successful with ID %s" % hierarchy_id)
                        return {"Hierarchy_Name": hierarchy_name}, hierarchy_id
            raise

    def create(self, hierarchy_name, level, hierarchy_filter, *args, **kwargs):
        return self.create_hierarchy(hierarchy_name, level, hierarchy_filter)

    # Use the new update API.
    def update(self, hierarchy_id, hierarchy_name, level, hierarchy_filter, *args, **kwargs):
        data, hierarchy_id = self.create(hierarchy_name, level, hierarchy_filter)
        print("Hierarchy -  update successful with ID %s" % hierarchy_id)
        return data, hierarchy_id

    # handling exception during delete, as update can fail if the previous explorer, metric rule or field has
    # already been deleted. This is required in case of multiple installation of
    # CF template with same names for metric rule, explorer view or fields
    def delete(self, hierarchy_id, hierarchy_name, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            # Backward Compatibility for 2.0.2 Versions.
            # If id is duplicate then get the id from explorer name and delete it.
            if hierarchy_id == "Duplicate":
                hierarchy_id = self.get_explorer_id(hierarchy_name)
            response = self.sumologic_cli.delete_hierarchy(hierarchy_id)
            print("Hierarchy - Completed the Hierarchy deletion for Name %s, response - %s"
                  % (hierarchy_name, response.text))
        else:
            print("Hierarchy - Skipping the Hierarchy deletion.")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        hierarchy_id = None
        if event.get('PhysicalResourceId'):
            _, hierarchy_id = event['PhysicalResourceId'].split("/")

        return {
            "hierarchy_name": props.get("HierarchyName"),
            "level": props.get("HierarchyLevel"),
            "hierarchy_filter": props.get("HierarchyFilter"),
            "hierarchy_id": hierarchy_id
        }


class SumoLogicMetricRules(SumoResource):

    def create_metric_rule(self, metric_rule_name, match_expression, variables, delete=True):
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
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'metrics:rule_name_already_exists' \
                            or error.get('code') == 'metrics:rule_already_exists':
                        print("METRIC RULES -  Duplicate Exists for Name %s" % metric_rule_name)
                        if delete:
                            self.delete(metric_rule_name, metric_rule_name, True)
                            # providing sleep for 10 seconds after delete.
                            time.sleep(uniform(2, 10))
                            return self.create_metric_rule(metric_rule_name, match_expression, variables, False)
                        return {"METRIC_RULES": metric_rule_name}, metric_rule_name
            raise

    def create(self, metric_rule_name, match_expression, variables, *args, **kwargs):
        return self.create_metric_rule(metric_rule_name, match_expression, variables)

    # No Update API. So, Metric rules can be updated and deleted from the main stack where it was created.
    def update(self, old_metric_rule_name, job_name, metric_rule_name, match_expression, variables, *args, **kwargs):
        # Need to add it because CF calls delete method if identifies change in metric rule name.
        self.delete(job_name, old_metric_rule_name, True)
        data, job_name = self.create_metric_rule(metric_rule_name, match_expression, variables)
        print("METRIC RULES -  Update successful with Name %s" % job_name)
        return data, job_name

    # handling exception during delete, as update can fail if the previous explorer, metric rule or field has
    # already been deleted. This is required in case of multiple installation of
    # CF template with same names for metric rule, explorer view or fields
    def delete(self, job_name, metric_rule_name, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            try:
                response = self.sumologic_cli.delete_metric_rule(metric_rule_name)
                print("METRIC RULES - Completed the Metric Rule deletion for Name %s, response - %s" % (metric_rule_name, response.text))
            except Exception as e:
                print("AWS EXPLORER - Exception while deleting the Metric Rules %s," % e)
        else:
            print("METRIC RULES - Skipping the Metric Rule deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        job_name = None
        if event.get('PhysicalResourceId'):
            _, job_name = event['PhysicalResourceId'].split("/")

        # Get previous Metric Rule Name
        old_metric_rule_name = None
        if "OldResourceProperties" in event and "MetricRuleName" in event['OldResourceProperties']:
            old_metric_rule_name = event["OldResourceProperties"]['MetricRuleName']

        variables = {}
        if "ExtractVariables" in props:
            variables = props.get("ExtractVariables")

        return {
            "metric_rule_name": props.get("MetricRuleName"),
            "match_expression": props.get("MatchExpression"),
            "variables": variables,
            "job_name": job_name,
            "old_metric_rule_name": old_metric_rule_name
        }


class SumoLogicUpdateFields(SumoResource):
    """
        This Class helps you to add fields to an existing source. This class will not create a new source if not already present.
        Fields can also be added to new Sources using AWSSource, HTTPSources classes.
        Getting collector name, as Calling custom collector resource can update the collector name if stack is updated with different collector name.
    """
    def add_fields_to_collector(self, collector_id, source_id, fields):
        if collector_id and source_id:
            sv, etag = self.sumologic_cli.source(collector_id, source_id)

            existing_fields = sv['source']['fields']

            new_fields = existing_fields.copy()
            new_fields.update(fields)

            sv['source']['fields'] = new_fields

            resp = self.sumologic_cli.update_source(collector_id, sv, etag)

            data = resp.json()['source']
            print("Added Fields in Source %s" % data["id"])

            return {"source_name": data["name"]}, str(source_id)
        return {"source_name": "Not updated"}, "No_Source_Id"

    def create(self, collector_id, source_id, fields, *args, **kwargs):
        return self.add_fields_to_collector(collector_id, source_id, fields)

    # Update the new fields to source.
    def update(self, collector_id, source_id, fields, old_resource_properties, *args,
               **kwargs):
        # Fetch the source, get all fields. Merge the Old and New fields and the update source.
        # If Source name or collector name is changed, it is create again.
        if 'SourceApiUrl' in old_resource_properties and \
                old_resource_properties['SourceApiUrl'].rsplit('/', 1)[-1] != source_id or \
                re.search('collectors/(.*)/sources', old_resource_properties['SourceApiUrl']).group(1) != collector_id:
            return self.create(collector_id, source_id, fields)
        else:
            sv, etag = self.sumologic_cli.source(collector_id, source_id)
            existing_source_fields = sv['source']['fields']
            if 'Fields' in old_resource_properties and old_resource_properties['Fields']:
                for k in old_resource_properties['Fields']:
                    existing_source_fields.pop(k, None)
            existing_source_fields.update(fields)

            sv['source']['fields'] = existing_source_fields
            resp = self.sumologic_cli.update_source(collector_id, sv, etag)
            data = resp.json()['source']
            print("updated Fields in Source %s" % data["id"])
            return {"source_name": data["name"]}, source_id

    def delete(self, collector_id, source_id, fields, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            sv, etag = self.sumologic_cli.source(collector_id, source_id)
            existing_fields = sv['source']['fields']

            if fields:
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

        old_resource_properties = None
        if "OldResourceProperties" in event:
            old_resource_properties = event['OldResourceProperties']

        fields = {}
        if "Fields" in props:
            fields = props.get("Fields")

        return {
            "fields": fields,
            "collector_id": re.search('collectors/(.*)/sources', props.get("SourceApiUrl")).group(1),
            "source_id": props.get("SourceApiUrl").rsplit('/', 1)[-1],
            "old_resource_properties": old_resource_properties
        }


class SumoLogicFieldExtractionRule(SumoResource):
    def _get_fer_by_name(self, fer_name):
        token = ""
        page_limit = 100
        response = self.sumologic_cli.get_all_field_extraction_rules(limit=page_limit, token=token)
        while response:
            print("calling FER API with token " + token)
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
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'fer:invalid_extraction_rule':
                        print("FER RULES -  Duplicate Exists for Name %s" % fer_name)
                        # check if there is difference in scope, if yes then merge the scopes.
                        fer_details = self._get_fer_by_name(fer_name)
                        change_in_fer = False
                        if "scope" in fer_details and fer_scope not in fer_details["scope"]:
                            fer_details["scope"] = fer_details["scope"] + " or " + fer_scope
                            change_in_fer = True
                        if "parseExpression" in fer_details and fer_expression not in fer_details["parseExpression"]:
                            fer_details["parseExpression"] = fer_expression
                            change_in_fer = True
                        if change_in_fer:
                            self.sumologic_cli.update_field_extraction_rules(fer_details["id"], fer_details)
                        return {"FER_RULES": fer_name}, fer_details["id"]
            raise

    def update(self, fer_id, fer_name, fer_scope, fer_expression, fer_enabled, *args, **kwargs):
        """
            Field Extraction Rule can be updated and deleted from the main stack where it was created.
            Update will update all the details in FER which are changed.
            Scope will be appended with OR conditions.
        """
        content = {
            "name": fer_name,
            "scope": fer_scope,
            "parseExpression": fer_expression,
            "enabled": fer_enabled
        }
        try:
            fer_details = self.sumologic_cli.get_fer_by_id(fer_id)
            # Use existing or append the new scope to existing scope.
            if "scope" in fer_details:
                if fer_scope not in fer_details["scope"]:
                    content["scope"] = fer_details["scope"] + " or " + fer_scope
                else:
                    content["scope"] = fer_details["scope"]

            response = self.sumologic_cli.update_field_extraction_rules(fer_id, content)
            job_id = response.json()["id"]
            print("FER RULES -  update successful with ID %s" % job_id)
            return {"FER_RULES": response.json()["name"]}, job_id
        except Exception as e:
            raise

    def delete(self, fer_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
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


class AddFieldsInHostMetricsSources(SumoResource):
    """
    This class is specifically designed for Adding fields to HostMetrics Source.
    """

    def batch_size_chunking(self, iterable, size=1):
        l = len(iterable)
        for idx in range(0, l, size):
            data = iterable[idx:min(idx + size, l)]
            yield data

    def get_source_and_collector_id(self, instances):
        ids = []
        for instance in instances:
            ids.append("InstanceId=%s" % instance["InstanceId"])
        query = " or ".join(ids)
        content = {
            "query": [
                {
                    "query": "_contentType=HostMetrics (%s) | count by _sourceId, _collectorId" % query,
                    "rowId": "A"
                }
            ],
            "startTime": int(time.time() * 1000) - 60 * 60 * 1000,
            "endTime": int(time.time() * 1000),
            "desiredQuantizationInSecs": 600,
            "requestedDataPoints": 1
        }
        output = self.sumologic_cli.fetch_metric_data_points(content)
        responses = json.loads(output.text)["response"]
        sources = []
        if responses:
            for response in responses:
                if "results" in response:
                    for result in response["results"]:
                        if "metric" in result and "dimensions" in result["metric"]:
                            output = {}
                            for dimension in result["metric"]["dimensions"]:
                                if dimension["key"] == "_collectorId" or dimension["key"] == "_sourceId":
                                    output[dimension["key"]] = str(int(dimension["value"], 16))
                            sources.append(output)
        return sources

    def add_remove_fields(self, region_value, account_id, new_fields, old_fields=None):
        # Get all EC2 Instance ID's
        ec2_resource = AWSResourcesProvider.get_provider("ec2", region_value, account_id)
        instance_ids = ec2_resource.fetch_resources()
        chucked_data = self.batch_size_chunking(instance_ids, 10)
        for instances in chucked_data:
            sources = self.get_source_and_collector_id(instances)
            for source in sources:
                collector_id = source["_collectorId"]
                source_id = source["_sourceId"]
                sv, etag = self.sumologic_cli.source(collector_id, source_id)
                existing_source_fields = sv['source']['fields']
                if old_fields:
                    for k in old_fields:
                        existing_source_fields.pop(k, None)
                if new_fields:
                    existing_source_fields.update(new_fields)

                sv['source']['fields'] = existing_source_fields
                resp = self.sumologic_cli.update_source(collector_id, sv, etag)
                data = resp.json()['source']
                print("updated Fields in Source %s" % data["id"])

    def create(self, region_value, account_id, fields, add_fields, *args, **kwargs):
        if add_fields:
            self.add_remove_fields(region_value, account_id, fields)
        else:
            print("Skipping Adding Fields to Sources for Region %s", region_value)
        return {"Fields_Added": "Successful"}, region_value

    def update(self, old_properties, region_value, account_id, fields, add_fields, *args, **kwargs):
        if add_fields:
            if old_properties['Region'] != region_value:
                data, region_value = self.create(region_value, account_id, fields, add_fields)
            else:
                old_fields = None
                if 'Fields' in old_properties and old_properties['Fields']:
                    old_fields = old_properties['Fields']
                self.add_remove_fields(region_value, account_id, fields, old_fields)
        else:
            print("Skipping Adding Fields to Sources for Region %s", region_value)
        return {"Fields_Updated": "Successful"}, region_value

    def delete(self, remove_on_delete_stack, region_value, account_id, fields, add_fields, *args, **kwargs):
        if add_fields:
            if remove_on_delete_stack:
                self.add_remove_fields(region_value, account_id, None, fields)
            else:
                print("UPDATE FIELDS - Skipping the Fields deletion")
        else:
            print("Skipping Adding Fields to Sources for Region %s", region_value)

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        fields = {}
        if "Fields" in props:
            fields = props.get("Fields")

        add_fields = True
        if props.get("AddFields") == "No":
            add_fields = False

        old_resource_properties = None
        if "OldResourceProperties" in event:
            old_resource_properties = event['OldResourceProperties']

        return {
            "region_value": props.get("Region"),
            "account_id": props.get("AccountID"),
            "fields": fields,
            "add_fields": add_fields,
            "remove_on_delete_stack": props.get("RemoveOnDeleteStack"),
            "old_properties": old_resource_properties
        }


class SumoLogicFieldsSchema(SumoResource):

    def get_field_id(self, field_name):
        all_fields = self.sumologic_cli.get_all_fields()
        if all_fields:
            for field in all_fields:
                if field_name == field["fieldName"]:
                    return field["fieldId"]
        raise Exception("Field Name with name %s not found" % field_name)

    def add_field(self, field_name):
        content = {
            "fieldName": field_name,
        }
        try:
            response = self.sumologic_cli.create_new_field(content)
            field_id = response["fieldId"]
            print("FIELD NAME -  creation successful with Field Id %s" % field_id)
            return {"FIELD_NAME": response["fieldName"]}, field_id
        except Exception as e:
            if hasattr(e, 'response') and "errors" in e.response.json() and e.response.json()["errors"]:
                errors = e.response.json()["errors"]
                for error in errors:
                    if error.get('code') == 'field:already_exists':
                        print("FIELD NAME -  Duplicate Exists for Name %s" % field_name)
                        # Get the Field ID from the existing fields.
                        field_id = self.get_field_id(field_name)
                        return {"FIELD_NAME": field_name}, field_id
            raise

    def create(self, field_name, *args, **kwargs):
        return self.add_field(field_name)

    # No Update API. So, Fields will be added and deleted from the main stack.
    def update(self, field_id, field_name, old_field_name, *args, **kwargs):
        # Create a new field when field name changes. Delete will happen for old Field. No Update API, so no updates.
        if field_name != old_field_name:
            return self.create(field_name)
        return {"FIELD_NAME": field_name}, field_id

    # handling exception during delete, as update can fail if the previous explorer, metric rule or field has
    # already been deleted. This is required in case of multiple installation of
    # CF template with same names for metric rule, explorer view or fields
    def delete(self, field_id, field_name, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            # Backward Compatibility for 2.0.2 Versions.
            # Check for field_id is duplicate, then get the field ID from name and delete the field.
            try:
                if field_id == "Duplicate":
                    field_id = self.get_field_id(field_name)
                response = self.sumologic_cli.delete_existing_field(field_id)
                print("FIELD NAME - Completed the Field deletion for ID %s, response - %s" % (field_id, response.text))
            except Exception as e:
                print("AWS EXPLORER - Exception while deleting the Field %s," % e)
        else:
            print("FIELD NAME - Skipping the Field deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        field_id = None
        if event.get('PhysicalResourceId'):
            _, field_id = event['PhysicalResourceId'].split("/")

        # Get previous Metric Rule Name
        old_field_name = None
        if "OldResourceProperties" in event and "FieldName" in event['OldResourceProperties']:
            old_field_name = event["OldResourceProperties"]['FieldName']

        return {
            "field_name": props.get("FieldName"),
            "field_id": field_id,
            "old_field_name": old_field_name
        }


class EnterpriseOrTrialAccountCheck(SumoResource):

    def check_account(self):
        is_enterprise = self.is_enterprise_or_trial_account()
        is_paid = "Yes"
        if not is_enterprise:
            all_apps = self.sumologic_cli.get_apps()
            if "apps" in all_apps and len(all_apps['apps']) <= 5:
                is_paid = "No"
        return {"is_enterprise": "Yes" if is_enterprise else "No", "is_paid": is_paid}, is_enterprise

    def create(self, *args, **kwargs):
        return self.check_account()

    def update(self, *args, **kwargs):
        return self.check_account()

    def delete(self, *args, **kwargs):
        print("In Delete method for Enterprise or Trial account")

    def extract_params(self, event):
        props = event.get("ResourceProperties")
        return props


class AlertsMonitor(SumoResource):

    def _replace_variables(self, appjson_filepath, variables):
        with open(appjson_filepath, 'r') as old_file:
            text = old_file.read()
            if variables:
                for k, v in variables.items():
                    text = text.replace("${%s}" % k, v)
            appjson = json.loads(text)

        return appjson

    def _get_content_from_s3(self, s3url, variables):
        with requests.get(s3url, stream=True) as r:
            r.raise_for_status()
            with tempfile.NamedTemporaryFile() as fp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fp.write(chunk)
                fp.flush()
                fp.seek(0)
                appjson = self._replace_variables(fp.name, variables)
        return appjson

    def _get_root_folder_id(self):
        response = self.sumologic_cli.get_root_folder()
        return response["id"]

    def import_monitor(self, folder_name, monitors3url, variables, suffix_date_time):
        date_format = "%d-%b-%Y %H:%M:%S"
        root_folder_id = self._get_root_folder_id()
        content = self._get_content_from_s3(monitors3url, variables)
        content["name"] = folder_name + " " + datetime.utcnow().strftime(date_format) if suffix_date_time \
            else folder_name
        response = self.sumologic_cli.import_monitors(root_folder_id, content)
        import_id = response["id"]
        print("ALERTS MONITORS - creation successful with ID %s and Name %s." % (import_id, folder_name))
        return {"ALERTS MONITORS": response["name"]}, import_id

    def create(self, folder_name, monitors3url, variables, suffix_date_time=False, *args, **kwargs):
        return self.import_monitor(folder_name, monitors3url, variables, suffix_date_time)

    def update(self, folder_id, folder_name, monitors3url, variables, suffix_date_time=False, retain_old_alerts=False, *args, **kwargs):
        data, new_folder_id = self.create(folder_name, monitors3url, variables, suffix_date_time)
        if retain_old_alerts:
            # Retaining old folder in the new folder as backup.
            old_folder = self.sumologic_cli.export_monitors(folder_id)
            old_folder["name"] = "Back Up " + old_folder["name"]
            self.sumologic_cli.import_monitors(new_folder_id, old_folder)
        print("ALERTS MONITORS - Update successful with ID %s." % new_folder_id)
        return data, new_folder_id

    def delete(self, folder_id, remove_on_delete_stack, *args, **kwargs):
        if remove_on_delete_stack:
            try:
                self.sumologic_cli.delete_monitor_folder(folder_id)
                print("ALERTS MONITORS - Completed the Deletion for Monitors Folder with ID " + str(folder_id))
            except Exception as e:
                print("ALERTS MONITORS - Exception while deleting the Monitors Folder %s," % e)
        else:
            print("ALERTS MONITORS - Skipping the Monitor Folder deletion")

    def extract_params(self, event):
        props = event.get("ResourceProperties")

        folder_id = None
        if event.get('PhysicalResourceId'):
            _, folder_id = event['PhysicalResourceId'].split("/")

        return {
            "folder_name": props.get("FolderName"),
            "monitors3url": props.get("MonitorsS3Url"),
            "variables": props.get("Variables"),
            "suffix_date_time": props.get("SuffixDateTime") == 'true',
            "retain_old_alerts": props.get("RetainOldAlerts") == 'true',
            "folder_id": folder_id,
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

