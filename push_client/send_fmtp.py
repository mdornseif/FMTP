#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

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


def upload_file(url, filename):
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
    headers = {'Content-Type': content_type}
    conn.request("POST", pasedurl.path, open(filename).read(), headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()


def main():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="upload this file", metavar="FILE")
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="URL of the endpoint")
    (options, args) = parser.parse_args()

    print "uploading %r to %r" % (options.filename, options.url)
    upload_file(options.url, options.filename)


if __name__ == "__main__":
    sys.exit(main())
