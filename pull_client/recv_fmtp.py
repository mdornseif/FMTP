#!/usr/bin/env python
# encoding: utf-8
"""
recv_fmtp.py - Reference implementation of a FMTP pull client (message receiver).

Created by Christian Klein on 2010-12-03.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import sys
from optparse import OptionParser
import httplib
import urlparse
import simplejson as json

help_message = '''
The help message goes here.
'''


def get_messages(url):
    """
    Receive list of messages
    """
    
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    headers = {'Accept': 'application/json'}
    conn.request("GET", parsedurl.path, headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()
    
    if response.status != 200:
        return []
    
    return json.load(response)


def get_message(url):
    """Read a single message"""
    
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    headers = {'Accept': 'application/json'}
    conn.request("GET", parsedurl.path, headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()
    
    if response.status != 200:
        return None
    
    return json.load(response)


def acknowledge(url):
    """Send acknowledgement for received message"""

    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    conn.request("DELETE", parsedurl.path)
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
    (options, args) = parser.parse_args()

    print "receiving list from %r" % options.url
    data = get_messages(options.endpoint)
    for message in data['messages']:
        url = message['url']
        payload = get_message(url)
        if payload:
            # Do something with message...
            print payload
            acknowledge(url)


if __name__ == "__main__":
    sys.exit(main())
