#!/usr/bin/env python
# encoding: utf-8
"""
push.py - Command line tool for FMTP push (message sender).

See https://github.com/hudora/FMTP for further information.

Created by Philipp Benjamin Köppchen on 2011-03-07.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.
"""
import mimetypes
import os
import optparse
import shutil
import sys

from fmtp_client import Queue, FmtpError


def main():
    """Main entry point"""
    parser = optparse.OptionParser()
    parser.add_option("-e", "--endpoint",
                      help="URL of the endpoint")
    parser.add_option("-c", "--credentials", dest="credentials",
                      help="Credentials (user:password)", default=None)
    parser.add_option("-s", "--source", help="Source directory", default=None)
    parser.add_option("-d", "--destination", help="Destination directory", default=None)

    options, args = parser.parse_args()

    if options.source and args:
        parser.error('Filenames from parameters and source directory is not allowed')
    elif not (options.source or args):
        parser.error('No filenames given')

    if not options.endpoint:
        parser.error('Please provide an endpoint (-e URL)')

    queue = Queue(options.endpoint, credentials=options.credentials)

    if args:
        filenames = args
    else:
        filenames = (os.path.abspath(os.path.join(options.source, filename))
                     for filename in os.listdir(options.source))

    for filename in filenames:
        try:
            with open(filename, 'rb') as fileobj:
                mimetype, _encoding = mimetypes.guess_type(filename)
                if mimetype is None:
                    mimetype = 'application/octet-stream'
                queue.post_message(os.path.basename(filename), mimetype, fileobj)
        except FmtpError as exception:
            sys.stderr.write('Error while transfering %s: %s\n' % (filename, str(exception)))
            sys.exit(1)

        if options.destination:
            newpath = os.path.abspath(os.path.join(options.destination, os.path.basename(filename)))
            shutil.move(filename, newpath)


if __name__ == "__main__":
    main()
