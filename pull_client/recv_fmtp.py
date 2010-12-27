#!/usr/bin/env python
# encoding: utf-8
"""
recv_fmtp.py - Reference implementation of a FMTP pull client (message receiver).

Created by Christian Klein on 2010-12-03.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import sys
import os
from optparse import OptionParser
import httplib
import urlparse
import xml.etree.ElementTree as ET
import simplejson as json

help_message = """Reference Implementation of a FMTP pull client"""


def get_messages(url, credentials=None):
    """
    Receive list of messages
    """
    
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    headers = {'Accept': 'application/xml'}
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())
    
    conn.request("GET", parsedurl.path, headers=headers)
    response = conn.getresponse()
    print response.status, response.reason
    content = response.read()
    conn.close()
    
    if response.status != 200:
        return []
    
    tree = ET.fromstring(content)
    return [msg.findtext('url') for msg in tree.findall('messages/message')]


def get_message(url, credentials=None):
    """Read a single message"""
    
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    headers = {}
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())
    
    conn.request("GET", parsedurl.path, headers=headers)
    response = conn.getresponse()
    print response.status, response.reason
    content = response.read()
    conn.close()
    
    if response.status != 200:
        return None
    
    return content


def acknowledge(url, credentials=None):
    """Send acknowledgement for received message"""

    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    headers = {}
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())
    
    conn.request("DELETE", parsedurl.path, headers=headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()

    if response.status != 204:
        return False
    return True


def main():
    parser = OptionParser()
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="URL of the endpoint")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials", default=None)
    parser.add_option("-d", "--directory", dest="directory",
                      help="Directory where documents will be stored", default=".")

    (options, args) = parser.parse_args()

    print "Receiving list from %r" % options.endpoint
    messages = get_messages(options.endpoint, credentials=options.credentials)
    print messages
    for url in messages:

        payload = get_message(url, credentials=options.credentials)
        if payload:
            path = urlparse.urlparse(url).path
            if path.endswith('/'):
                path = path[:-1]
            filename = os.path.join(options.directory, os.path.split(path)[-1])
            f = open(filename, 'w')
            f.write(payload)
            f.close()
            acknowledge(url, credentials=options.credentials)


if __name__ == "__main__":
    sys.exit(main())
