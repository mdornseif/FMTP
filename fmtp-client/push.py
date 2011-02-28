#!/usr/bin/env python
# encoding: utf-8
"""
pull.py - Command line tool for FMTP push (message sender).

See https://github.com/hudora/FMTP for further information.

Created by Philipp Benjamin Köppchen on 2011-03-07.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.
"""
from __future__ import with_statement

from os.path import basename
from optparse import OptionParser

from fmtp_client import Queue, FmtpError


def main():
    # Parse Commandline
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="upload this file", metavar="FILE")
    parser.add_option("-e", "--endpoint",
                      help="URL of the endpoint")
    parser.add_option("-g", "--guid", default='',
                      help="GUID of the message [default: filename]")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials (user:password)", default=None)
    (options, args) = parser.parse_args()

    if args:
        parser.error('No positional arguments are accepted')

    if not options.endpoint:
        parser.error('Please provide an endpoint (-e URL)')
    if not options.filename:
        parser.error('Please provide a file to upload (-f FILENAME)')

    # If no GUID is given use Filename
    guid = options.guid
    if not guid:
        guid = basename(options.filename)
    print "uploading %r to %r" % (options.filename, options.endpoint)

    queue = Queue(options.endpoint, credentials=options.credentials)

    try:
        with open(options.filename, 'rb') as fp:
            queue.post_message(guid, 'application/octet-stream', fp.read())
    except FmtpError, e:
        parser.error(e)


if __name__ == "__main__":
    main()
