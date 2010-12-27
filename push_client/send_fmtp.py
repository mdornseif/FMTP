#!/usr/bin/env python
# encoding: utf-8
"""
send_fmtp.py

Created by Maximillian Dornseif on 2010-11-16.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

import sys
from optparse import OptionParser
import httplib
import urllib
import urlparse
import mimetypes

help_message = '''
The help message goes here.
'''


def upload_file(url, filename, credentials=None):
    """Uploads a file to a Frugal Message Trasfer Protocol (FMTP) Server."""
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    params = urllib.urlencode({'spam': 1, 'eggs': 2, 'bacon': 0})
    content_type = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'
    else:
        content_type = content_type[0]
    headers = {'Content-Type': content_type}
    
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())
    conn.request("POST", parsedurl.path, open(filename).read(), headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()


def main():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="upload this file", metavar="FILE")
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="URL of the endpoint")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials", default=None)
    
    (options, args) = parser.parse_args()

    print "uploading %r to %r" % (options.filename, options.endpoint)
    upload_file(options.endpoint, options.filename, options.credentials)


if __name__ == "__main__":
    sys.exit(main())
