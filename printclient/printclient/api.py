
from __future__ import with_statement

import os
import shutil
import urllib
import urllib2
import tempfile
import base64

from simplejson import loads


class Job(object):
    
    file_name = None
    deleted = False
    
    def __init__(self, api, url):
        self.url = url
        self.api = api
    
    def fetch(self):
        data = self.api.fetch(self.url)
        self.file_name = tempfile.mktemp(suffix='.pdf')
        with open(self.file_name, 'wb') as F:
            F.write(data)
    
    def delete(self):
        if not self.deleted:
            self.api.delete(self.url)
            self.deleted = True


class PrintServerAPI(object):
    
    def __init__(self, config):
        self.config = config
    
    def _make_headers(self):
        auth_string = base64.encodestring('%(username)s:%(password)s' % self.config)[:-1]
        return {"Authorization": "Basic %s" % auth_string}
    
    def fetch(self, url):
        headers = self._make_headers()
        req = urllib2.Request(url, headers=headers)
        return urllib2.urlopen(req).read()
    
    def list_jobs(self):
        try:
            text = self.fetch(self.config['server_url'])
        except urllib2.URLError, exc:
            logging.error('Error while retrieving job list: %s' % str(exc))
            return []
        json = loads(text)
        return [Job(self, url) for url in json['jobs']]
    
    def delete(self, url):
        headers = self._make_headers()
        req = DeleteRequest(url, headers=headers)
        try:
            return urllib2.urlopen(req).read()
        except Exception, E:
            if '204' in str(E):
                return
            raise

    def fetch2(self, url, method="GET", body=None):
        headers = self._make_headers()
        response, content = self.http.request(url, method, body=body, headers=headers)
        if method == "GET":
            expected_status = 200
        elif method == "DELETE":
            expected_status = 204
        else:
            expected_status = 200
        if response.status != expected_status:
            logging.error('%s: %s, expected: %s' % (url, response.status, expected_status))
            raise RuntimeError('%s: %s, expected: %s (%s)' % (url, response.status, expected_status, content))        
        return content


class DeleteRequest(urllib2.Request):
    
    def get_method(self):
        return 'DELETE'

