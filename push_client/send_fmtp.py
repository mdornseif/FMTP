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
import os.path


def upload_file(url, filename, guid):
    """Uploads a file to a Frugal Message Trasfer Protocol (FMTP) Server."""
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    content_type = mimetypes.guess_type(filename)[0]
    if not content_type:
        content_type = 'application/octet-stream'
    else:
        content_type = content_type[0]
    headers = {'Content-Type': content_type}
    path = parsedurl.path + urllib.quote(guid)
    conn.request("POST", path, open(filename).read(), headers)
    response = conn.getresponse()
    print response.status, response.reason
    conn.close()


def main():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="upload this file", metavar="FILE")
    parser.add_option("-e", "--endpoint",
                      help="URL of the endpoint")
    parser.add_option("-g", "--guid", default = '',
                      help="GUID of the message [default: filename]")
    (options, args) = parser.parse_args()

    guid = options.guid
    if not guid:
        guid = os.path.basename(options.filename)
    print "uploading %r to %r" % (options.filename, options.endpoint)
    upload_file(options.endpoint, options.filename, guid)


if __name__ == "__main__":
    sys.exit(main())
