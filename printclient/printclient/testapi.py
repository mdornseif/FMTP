
import os
import shutil
import urllib
import urllib2
import tempfile
from simplejson import loads


class Job(object):
    
    file_name = None
    
    def __init__(self, file_name):
        self.file_name = file_name
    
    def fetch(self):
        pass
    
    def delete(self):
        pass


class PrintServerAPI(object):
    
    test_jobs = ['test.pdf']
    
    def __init__(self, config):
        self.config = config
    
    def list_jobs(self):
        if self.test_jobs:
            file_name = self.test_jobs.pop(0)
            return [Job(file_name)]
        return []
