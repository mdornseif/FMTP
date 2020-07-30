#!/usr/bin/env python
# encoding: utf-8
"""
pull.py - Command line tool for FMTP pull (message receiver).

See https://github.com/hudora/FMTP for further information.

Created by Philipp Benjamin Köppchen on 2011-03-07.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.
"""
from __future__ import with_statement

import os.path
from optparse import OptionParser
import urlparse

from fmtp_client import Queue, FmtpError


def construct_filename(url):
    """Ermittelt einen Dateinamen aus einer URL.

    >>> construct_filename('http://example.com/fmtp/chat/123/')
    '123'

    """
    path = urlparse.urlparse(url).path
    path = path.rstrip('/')
    return os.path.split(path)[-1]


def main():
    parser = OptionParser()
    parser.add_option("-e", "--endpoint", dest="endpoint",
                      help="URL of the endpoint")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials", default=None)
    parser.add_option("-d", "--directory", dest="directory",
                      help="Directory where documents will be stored [%default]", default="./")

    (options, args) = parser.parse_args()

    if args:
        parser.error('No positional arguments are accepted')

    if not options.endpoint:
        parser.error('Please provide an endpoint (-e URL)')

    print "Receiving list from %r" % options.endpoint

    queue = Queue(options.endpoint, credentials=options.credentials)

    for message in queue:
        print "Receiving Message from %r" % message.url
        filename = os.path.join(options.directory, construct_filename(message.url))

        with open(filename, 'wb') as fp:
            fp.write(message.content)

        print "Acknowledging Message from %s" % message.url
        message.acknowledge()


if __name__ == "__main__":
    main()
