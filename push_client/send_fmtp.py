#!/usr/bin/env python
# encoding: utf-8
"""
send_fmtp.py - minimal Implementation of an FMTP "pull" Client.
See https://github.com/hudora/FMTP for further information.

Created by Maximillian Dornseif on 2010-11-16.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.
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
from optparse import OptionParser
import httplib
import urllib
import urlparse
import mimetypes
import os.path


def upload_file(url, filename, guid, credentials=None):
    """Uploads a file to a Frugal Message Trasfer Protocol (FMTP) Server."""

    # Decide if we should use HTTP oer HTTPS
    parsedurl = urlparse.urlparse(url)
    if parsedurl.scheme == 'https':
        conn = httplib.HTTPSConnection(parsedurl.netloc)
    else:
        conn = httplib.HTTPConnection(parsedurl.netloc)
    
    # Find content-type by inspecting the file name
    content_type = mimetypes.guess_type(filename)[0]
    if not content_type:
        content_type = 'application/octet-stream'
    else:
        content_type = content_type[0]
    headers = {'Content-Type': content_type}
    
    # Add Passwort
    if credentials:
        headers['Authorization'] = 'Basic %s' % (credentials.encode('base64').strip())

    # Add slash if missing
    path = parsedurl.path
    if not path.endswith('/'):
        path = path + '/'
    path = parsedurl.path + urllib.quote(guid)
    
    # Upload the file
    conn.request("POST", path, open(filename).read(), headers)

    # Read the Response
    response = conn.getresponse()
    # for debugging: print response.status, response.reason
    conn.close()


def main():
    # Parse Commandline
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="upload this file", metavar="FILE")
    parser.add_option("-e", "--endpoint",
                      help="URL of the endpoint")
    parser.add_option("-g", "--guid", default = '',
                      help="GUID of the message [default: filename]")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials (user:password)", default=None)
    (options, args) = parser.parse_args()

    # If no GUID is given use Filename
    guid = options.guid
    if not guid:
        guid = os.path.basename(options.filename)
    print "uploading %r to %r" % (options.filename, options.endpoint)

    # Initiate the actual Upload
    upload_file(options.endpoint, options.filename, guid, options.credentials)


if __name__ == "__main__":
    main()
