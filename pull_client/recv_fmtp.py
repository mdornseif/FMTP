#!/usr/bin/env python
# encoding: utf-8
"""
recv_fmtp.py - Reference implementation of a FMTP pull client (message receiver).

Created by Christian Klein on 2010-12-03.
"""

# Copyright (c) 2010, 2011 HUDORA GmbH. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this list of
#       conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright notice, this list
#       of conditions and the following disclaimer in the documentation and/or other materials
#       provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY HUDORA ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL <COPYRIGHT HOLDER> OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of HUDORA.


import sys
import os
from optparse import OptionParser
import httplib
import urlparse
import xml.etree.ElementTree as ET
import simplejson as json


def get_connection(url, credentials):
    """Set up HTTP Connection"""
    # Decide if we should use HTTP oer HTTPS
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)

    headers = {}
    # Add Passwort
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())
    return conn, parsedurl, headers


def get_messages(url, credentials=None):
    """Receive list of unfetched messages"""
    conn, parsedurl, headers = get_connection(url, credentials)
    headers.update({'Accept': 'application/xml'})
    # Request list of Messages
    conn.request("GET", path, headers=headers)
    response = conn.getresponse()
    # for debugging: print response.status, response.reason
    content = response.read()
    conn.close()
    # Request successfull?
    if response.status != 200:
        # No: print what we got and return an empty list of messages
        print response.status, response.reason
        return []
    # Parse XML and return message URLs
    tree = ET.fromstring(content)
    return [msg.findtext('url') for msg in tree.findall('messages/message')]


def get_message(url, credentials=None):
    """Read a single message"""
    # Request list of Messages
    conn, parsedurl, headers = get_connection(url, credentials)
    conn.request("GET", parsedurl.path, headers=headers)
    # get response
    response = conn.getresponse()
    content = response.read()
    conn.close()
    # Request successfull?
    if response.status != 200:
        # No: print what we got and return empty data
        print response.status, response.reason
        return None
    return content


def acknowledge(url, credentials=None):
    """Send acknowledgement for received message telling the server we have saved it."""

    conn, parsedurl, headers = get_connection(url, credentials)
    conn.request("DELETE", parsedurl.path, headers=headers)
    response = conn.getresponse()
    conn.close()

    if response.status != 204:
        # Something went wrong!
        print response.status, response.reason
        return False
    return True


def main():
    parser = OptionParser()
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="URL of the endpoint")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials", default=None)
    parser.add_option("-d", "--directory", dest="directory",
                      help="Directory where documents will be stored [%default]", default="./")

    (options, args) = parser.parse_args()

    print "Receiving list from %r" % options.endpoint
    # Strategy: Request a list of messages, retrieve each message in the list,
    # then delete/acknowledge each Message retrieved
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
