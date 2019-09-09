from abc import ABCMeta, abstractmethod
import six
import re
import json
import requests
from sumologic import SumoLogic
import tempfile
from datetime import datetime
import time


class ResourceFactory(object):
    resource_type = {}

    @classmethod
    def register(cls, objname, obj):
        print("registering", obj, objname)
        if objname != "Resource":
            cls.resource_type[objname] = obj

    @classmethod
    def get_resource(cls, objname):
        if objname in cls.resource_type:
            return cls.resource_type[objname]
        raise Exception("%s resource type is undefined" % objname)


class AutoRegisterResource(ABCMeta):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(AutoRegisterResource, cls).__new__(cls, clsname, bases, attrs)
        ResourceFactory.register(clsname, newclass)
        return newclass


@six.add_metaclass(AutoRegisterResource)
class Resource(object):

    def __init__(self, access_id, access_key, deployment):
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
        elif self.deployment in ["ca", "au", "de", "eu", "jp", "us2"]:
            return "https://api.%s.sumologic.com/api" % self.deployment
        else:
            return 'https://%s-api.sumologic.net/api' % self.deployment

    def is_enterprise_or_trial_account(self):
        to_time = int(time.time())*1000
        from_time = to_time - 5*60*1000
        try:
            response = self.sumologic_cli.search_job("benchmarkcat guardduty", fromTime=from_time, toTime=to_time)
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


class Collector(Resource):
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

    def update(self, collector_id, collector_type, collector_name, source_category=None, description=None, *args, **kwargs):
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


class S3Source(Resource):
    pass


class HTTPSource(Resource):

    def create(self, collector_id, source_name, source_category,
        date_format=None, date_locator="\"timestamp\": (.*),", *args, **kwargs):

        endpoint = source_id = None
        params = {
            "sourceType": "HTTP",
            "name": source_name,
            "messagePerRequest": False,
            "category": source_category
        }
        if date_format:
            params["defaultDateFormats"] = [{"format": date_format, "locator": date_locator}]
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

    def update(self, collector_id, source_id, source_name, source_category, date_format=None, date_locator=None, *args, **kwargs):
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
        return {
            "collector_id": props.get("CollectorId"),
            "source_name": props.get("SourceName"),
            "source_category": props.get("SourceCategory"),
            "date_format": props.get("DateFormat"),
            "date_locator": props.get("DateLocatorRegex"),
            "source_id": source_id
        }


class App(Resource):

    def _convert_absolute_time(self, start, end):
        return {

            "type": "BeginBoundedTimeRange",
            "from": {
                "type": "EpochTimeRangeBoundary",
                "epochMillis": start
            },
            "to": {
                "type": "EpochTimeRangeBoundary",
                "epochMillis": end
            }

        }

    def _convert_to_hour(self, timeoffset):
        hour = timeoffset/60*60*1000
        return "%sh" % (hour)

    def _convert_relative_time(self, timeoffset):
        return{
            "type": "BeginBoundedTimeRange",
            "from": {
                "type": "RelativeTimeRangeBoundary",
                "relativeTime": self._convert_to_hour(timeoffset)
            },
            "to": None
        }

    def _convert_to_api_format(self, appjson):
        appjson['type'] = "FolderSyncDefinition"
        for child in appjson['children']:
            if 'columns' in child:
                del child['columns']
            if child['type'] == "Report":
                child['type'] = "DashboardSyncDefinition"
                for panel in child['panels']:
                    if 'fields' in panel:
                        del panel['fields']
                    if 'type' in panel:
                        del panel['type']
                    if 'isDisabled' in panel:
                        del panel['isDisabled']
                    timejson = json.loads(panel['timeRange'])
                    if "absolute" in panel['timeRange']:
                        panel['timeRange'] = self._convert_absolute_time(timejson[0]['d'], timejson[0]['d'])
                    else:
                        panel['timeRange'] = self._convert_relative_time(timejson[0]['d'])
                for dfilter in child.get('filters', []):
                    if not "defaultValue" in dfilter:
                        dfilter['defaultValue'] = None
                    del dfilter['type']

            elif child['type'] == "Search":
                child['type'] = "SavedSearchWithScheduleSyncDefinition"
                child['search'] = {
                    'type': 'SavedSearchSyncDefinition',
                    'defaultTimeRange': child.pop('defaultTimeRange'),
                    'byReceiptTime': False,
                    'viewName': child.pop('viewNameOpt'),
                    'viewStartTime': child.pop('viewStartTimeOpt'),
                    'queryText': child.pop('searchQuery')
                }
                if 'queryParameters' in child:
                    child['search']['queryParameters'] = child.pop('queryParameters')
            elif child['type'] == 'Folder':
                # taking care of folder in folder case
                child.update(self.convert_to_api_format(child))

        return appjson

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
                # appjson = self._convert_to_api_format(appjson)
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

    def create(self, appname, source_params, *args, **kwargs):
        # Add  retry if folder sync fails
        if appname == "Amazon GuardDuty Benchmark" and not self.is_enterprise_or_trial_account():
            raise Exception("%s is available to Enterprise or Trial Account Type only." % appname)

        content = self._get_app_content(appname, source_params)
        response = self.sumologic_cli.get_personal_folder()
        personal_folder_id = response.json()['id']
        app_folder_id = self._get_app_folder(content, personal_folder_id)
        response = self.sumologic_cli.import_content(personal_folder_id, content, is_overwrite="true")
        job_id = response.json()["id"]
        print("installed app %s: appFolderId: %s personalFolderId: %s jobId: %s" % (
            appname, app_folder_id, personal_folder_id, job_id))
        self._wait_for_folder_creation(personal_folder_id, job_id)
        return {"APP_FOLDER_NAME": content["name"]}, app_folder_id

    def update(self, app_folder_id, appname, source_params, *args, **kwargs):
        self.delete(app_folder_id, remove_on_delete_stack=True)
        data, app_folder_id = self.create(appname, source_params)
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
            "appname": props.get("AppName"),
            "source_params": props.get("AppSources"),
            "app_folder_id": app_folder_id
        }

if __name__ == '__main__':

    params = {

        "access_id": "",
        "access_key": "",
        "deployment": ""

    }
    collector_id = None
    collector_type = "Hosted"
    collector_name = "GuarddutyCollector"
    source_name = "GuarddutyEvents"
    source_category = "Labs/AWS/Guardduty"
    appname = "Amazon GuardDuty Benchmark"
    source_params = {
        "logsrc": "_sourceCategory=%s" % source_category
    }
    col = Collector(**params)
    src = HTTPSource(**params)
    app = App(**params)

    # create
    _, collector_id = col.create(collector_type, collector_name, source_category)
    _, source_id = src.create(collector_id, source_name, source_category)
    _, app_folder_id = app.create(appname, source_params)


    # update
    _, new_collector_id = col.update(collector_id, collector_type, "GuarddutyCollectorNew", "Labs/AWS/GuarddutyNew", description="Guardduty Collector")
    assert(collector_id == new_collector_id)
    _, new_source_id = src.update(collector_id, source_id, "GuarddutyEventsNew", "Labs/AWS/GuarddutyNew", date_format="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", date_locator='\"createTime\":(.*),')
    assert(source_id == new_source_id)
    new_source_params = {
        "logsrc": "_sourceCategory=%s" % "Labs/AWS/GuarddutyNew"
    }
    _, new_app_folder_id = app.update(app_folder_id, appname, new_source_params)
    assert(app_folder_id != new_app_folder_id)

    # delete
    src.delete(collector_id, source_id, True)
    col.delete(collector_id, True)
    app.delete(new_app_folder_id, True)

