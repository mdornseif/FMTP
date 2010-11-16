#!/usr/bin/env python
# encoding: utf-8
"""
fmtp-server/mail.py

Created by Maximillian Dornseif on 2010-11-16.
Copyright (c) 2010 HUDORA. All rights reserved.
"""


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db


class Message(db.Model):
    guid = db.StringProperty(required=True)
    content_type = db.StringProperty(required=True)
    body = db.BlobProperty(required=True)
    status = db.StringProperty(required=True, default='new', choices=('new', 'deleted'))
    created_at = db.DateTimeProperty(auto_now_add=True)


class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!')


class MessageHandler(webapp.RequestHandler):
    def get(self, guid):
        message = Message.all.filter('guid =', guid).get()
        if not message:
            self.response.set_status(404)  # 404 Not Found
            self.response.out.write('not found')
        if message.status == 'deleted':
            self.response.set_status(410)  # 410 Gone
            self.response.out.write('already deleted')
        else:
            if message.content_type:
                self.response.headers["Content-Type"] = message.content_type
            else:
                self.response.headers["Content-Type"] = 'application/octet-stream'
            self.response.set_status(200)  # ok
            self.response.out.write(message.body)

    def post(self, guid):
        message = Message.all.filter('guid =', guid).get()
        if message:
            if message.status == 'deleted':
                self.response.set_status(410)  # 410 Gone
                self.response.out.write('already deleted')
            else:
                self.response.set_status(409)  # 409 Conflict
                self.response.out.write('already exists')
        else:
            Message.get_or_insert(guid, body=request.body, content_type=request.headers.get('Content-Type'))
            self.response.set_status(204)  # no content
            self.response.out.write('saved')

    def delete(self, guid):
        message = Message.all.filter('guid =', guid).get()
        if not message:
            self.response.set_status(404)  # 404 Not Found
            self.response.out.write('not found')
        if message.status == 'deleted':
            self.response.set_status(410)  # 410 Gone
            self.response.out.write('already deleted')
        else:
        message.status = 'deleted'
        message.put()
        self.response.set_status(204)  # no content
        self.response.out.write('deleted')


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/(.*)', MessageHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
