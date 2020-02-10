import json
import requests
import time
import random

try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

DEFAULT_VERSION = 'v1'


class SumoLogic(object):

    def __init__(self, accessId, accessKey, endpoint=None, cookieFile='cookies.txt'):
        self.session = requests.Session()
        self.session.auth = (accessId, accessKey)
        self.session.headers = {'content-type': 'application/json', 'accept': 'application/json'}
        cj = cookielib.FileCookieJar(cookieFile)
        self.session.cookies = cj
        if endpoint is None:
            self.endpoint = self._get_endpoint()
        else:
            self.endpoint = endpoint
        if self.endpoint[-1:] == "/":
            raise Exception("Endpoint should not end with a slash character")

    def _get_endpoint(self):
        """
        SumoLogic REST API endpoint changes based on the geo location of the client.
        For example, If the client geolocation is Australia then the REST end point is
        https://api.au.sumologic.com/api/v1
        When the default REST endpoint (https://api.sumologic.com/api/v1) is used the server
        responds with a 401 and causes the SumoLogic class instantiation to fail and this very
        unhelpful message is shown 'Full authentication is required to access this resource'
        This method makes a request to the default REST endpoint and resolves the 401 to learn
        the right endpoint
        """
        self.endpoint = 'https://api.sumologic.com/api'
        self.response = self.session.get('https://api.sumologic.com/api/v1/collectors')  # Dummy call to get endpoint
        endpoint = self.response.url.replace('/v1/collectors', '')  # dirty hack to sanitise URI and retain domain
        print("SDK Endpoint", endpoint)
        return endpoint

    def get_versioned_endpoint(self, version):
        return self.endpoint + '/%s' % version

    def delete(self, method, params=None, version=DEFAULT_VERSION):
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.delete(endpoint + method, params=params)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def get(self, method, params=None, version=DEFAULT_VERSION):
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.get(endpoint + method, params=params)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def post(self, method, params, headers=None, version=DEFAULT_VERSION):
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.post(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def put(self, method, params, headers=None, version=DEFAULT_VERSION):
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.put(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def search(self, query, fromTime=None, toTime=None, timeZone='UTC'):
        params = {'q': query, 'from': fromTime, 'to': toTime, 'tz': timeZone}
        r = self.get('/logs/search', params)
        return json.loads(r.text)

    def search_job(self, query, fromTime=None, toTime=None, timeZone='UTC', byReceiptTime=None):
        params = {'query': query, 'from': fromTime, 'to': toTime, 'timeZone': timeZone, 'byReceiptTime': byReceiptTime}
        r = self.post('/search/jobs', params)
        return json.loads(r.text)

    def search_job_status(self, search_job):
        r = self.get('/search/jobs/' + str(search_job['id']))
        return json.loads(r.text)

    def search_job_messages(self, search_job, limit=None, offset=0):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/search/jobs/' + str(search_job['id']) + '/messages', params)
        return json.loads(r.text)

    def search_job_records(self, search_job, limit=None, offset=0):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/search/jobs/' + str(search_job['id']) + '/records', params)
        return json.loads(r.text)

    def delete_search_job(self, search_job):
        return self.delete('/search/jobs/' + str(search_job['id']))

    def connection(self, connection_id):
        r = self.get('/connections/' + str(connection_id))
        return json.loads(r.text), r.headers['etag']

    def create_connection(self, connection, headers=None):
        return self.post('/connections', connection, headers)

    def update_connection(self, connection, etag):
        headers = {'If-Match': etag}
        return self.put('/connections/' + str(connection['connection']['id']), connection, headers)

    def delete_connection(self, connection_id, type):
        return self.delete('/connections/' + connection_id + '?type=' + type)

    def collectors(self, limit=None, offset=None, filter_type=None):
        params = {'limit': limit, 'offset': offset}
        if filter_type:
            params['filter'] = filter_type
        r = self.get('/collectors', params)
        return json.loads(r.text)['collectors']

    def collector(self, collector_id):
        r = self.get('/collectors/' + str(collector_id))
        return json.loads(r.text), r.headers['etag']

    def create_collector(self, collector, headers=None):
        return self.post('/collectors', collector, headers)

    def update_collector(self, collector, etag):
        headers = {'If-Match': etag}
        return self.put('/collectors/' + str(collector['collector']['id']), collector, headers)

    def delete_collector(self, collector):
        return self.delete('/collectors/' + str(collector['collector']['id']))

    def sources(self, collector_id, limit=None, offset=None):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/collectors/' + str(collector_id) + '/sources', params)
        return json.loads(r.text)['sources']

    def source(self, collector_id, source_id):
        r = self.get('/collectors/' + str(collector_id) + '/sources/' + str(source_id))
        return json.loads(r.text), r.headers['etag']

    def create_source(self, collector_id, source):
        return self.post('/collectors/' + str(collector_id) + '/sources', source)

    def update_source(self, collector_id, source, etag):
        headers = {'If-Match': etag}
        return self.put('/collectors/' + str(collector_id) + '/sources/' + str(source['source']['id']), source, headers)

    def delete_source(self, collector_id, source):
        return self.delete('/collectors/' + str(collector_id) + '/sources/' + str(source['source']['id']))

    def dashboards(self, monitors=False):
        params = {'monitors': monitors}
        r = self.get('/dashboards', params)
        return json.loads(r.text)['dashboards']

    def dashboard(self, dashboard_id):
        r = self.get('/dashboards/' + str(dashboard_id))
        return json.loads(r.text)['dashboard']

    def dashboard_data(self, dashboard_id):
        r = self.get('/dashboards/' + str(dashboard_id) + '/data')
        return json.loads(r.text)['dashboardMonitorDatas']

    def search_metrics(self, query, fromTime=None, toTime=None, requestedDataPoints=600, maxDataPoints=800):
        '''Perform a single Sumo metrics query'''

        def millisectimestamp(ts):
            '''Convert UNIX timestamp to milliseconds'''
            if ts > 10 ** 12:
                ts = ts / (10 ** (len(str(ts)) - 13))
            else:
                ts = ts * 10 ** (12 - len(str(ts)))
            return int(ts)

        params = {'query': [{"query": query, "rowId": "A"}],
                  'startTime': millisectimestamp(fromTime),
                  'endTime': millisectimestamp(toTime),
                  'requestedDataPoints': requestedDataPoints,
                  'maxDataPoints': maxDataPoints}
        r = self.post('/metrics/results', params)
        return json.loads(r.text)

    def delete_folder(self, folder_id):
        return self.delete('/content/%s/delete' % folder_id, version='v2')

    def create_folder(self, name, description, parent_folder_id):
        content = {
            "name": name,
            "description": description,
            "parentId": parent_folder_id
        }
        return self.post('/content/folders', params=content, version='v2')

    def get_personal_folder(self):
        return self.get('/content/folders/personal', version='v2')

    def import_content(self, folder_id, content, is_overwrite="false"):
        return self.post('/content/folders/%s/import?overwrite=%s' % (folder_id, is_overwrite), params=content,
                         version='v2')

    def check_import_status(self, folder_id, job_id):
        return self.get('/content/folders/%s/import/%s/status' % (folder_id, job_id), version='v2')

    def install_app(self, app_id, content):
        time.sleep(random.randint(1, 10))
        return self.post('/apps/%s/install' % (app_id), params=content)

    def check_app_install_status(self, job_id):
        return self.get('/apps/install/%s/status' % job_id)

    def create_explorer_view(self, content):
        return self.post('/topologies', params=content, version='v1alpha')

    def delete_explorer_view(self, explorer_id):
        return self.delete('/topologies/%s' % explorer_id, version='v1alpha')

    def create_metric_rule(self, content):
        return self.post('/metricsRules', params=content)

    def delete_metric_rule(self, metric_rule_name):
        return self.delete('/metricsRules/%s' % metric_rule_name)

    def create_field_extraction_rule(self, content):
        return self.post('/extractionRules', params=content)

    def delete_field_extraction_rule(self, fer_name):
        return self.delete('/extractionRules/%s' % fer_name)

    def get_all_field_extraction_rules(self, limit=None, token=None,):
        params = {'limit': limit, 'token': token}
        r = self.get('/extractionRules', params)
        return json.loads(r.text)

    def update_field_extraction_rules(self, fer_id, fer_details):
        return self.put('/extractionRules/%s' % fer_id, fer_details)
