#!/usr/bin/env python
# encoding: utf-8
"""
fmtp-server/main.py

Created by Maximillian Dornseif on 2010-11-16.
Copyright (c) 2010 HUDORA. All rights reserved.
"""


from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
import xml.etree.cElementTree as ET
import urlparse
import urllib


class Message(db.Model):
    guid = db.StringProperty(required=True)
    content_type = db.StringProperty(required=True)
    body = db.BlobProperty(required=True)
    status = db.StringProperty(required=True, default='new', choices=('new', 'deleted'))
    created_at = db.DateTimeProperty(auto_now_add=True)


# Code is based on http://code.activestate.com/recipes/573463/
# and huTools.structures
def _convert_dict_to_xml_recurse(parent, dictitem, listnames):
    # we can't convert bare lists
    assert not isinstance(dictitem, list)

    if isinstance(dictitem, dict):
        for (tag, child) in sorted(dictitem.iteritems()):
            if isinstance(child, list):
                # iterate through the array and convert
                listelem = ET.Element(tag)
                parent.append(listelem)
                for listchild in child:
                    elem = ET.Element(listnames.get(tag, 'item'))
                    listelem.append(elem)
                    _convert_dict_to_xml_recurse(elem, listchild, listnames)
            else:
                elem = ET.Element(tag)
                parent.append(elem)
                _convert_dict_to_xml_recurse(elem, child, listnames)
    elif not dictitem is None:
        parent.text = unicode(dictitem)


def dict2et(xmldict, roottag='data', listnames=None):
    if not listnames:
        listnames = {}
    root = ET.Element(roottag)
    _convert_dict_to_xml_recurse(root, xmldict, listnames)
    return root


def dict2xml(datadict, roottag='data', listnames=None, pretty=False):
    tree = dict2et(datadict, roottag, listnames)
    if pretty:
        indent(tree)
    return ET.tostring(tree, 'utf-8')


class MainHandler(webapp.RequestHandler):
    def get(self):
        messages = Message.all().filter('status =', 'new').fetch(10)
        self.response.set_status(200)  # ok
        if self.request.headers.get('Accept', '').startswith('application/json'):
            self.response.headers["Content-Type"] = 'application/json'
            ret = {'min_retry_interval': 500, 'max_retry_interval': 60000, 'messages': []}
            for message in messages:
                ret['messages'].append(dict(url=urlparse.urljoin(self.request.uri, urllib.quote(message.guid)),
                                            created_at=str(message.created_at)))
            self.response.out.write(simplejson.dumps(ret))
        elif self.request.headers.get('Accept', '').startswith('application/xml'):
            self.response.headers["Content-Type"] = 'application/xml'
            ret = {'min_retry_interval': 500, 'max_retry_interval': 60000, 'messages': []}
            for message in messages:
                ret['messages'].append(dict(url=urlparse.urljoin(self.request.uri, urllib.quote(message.guid)),
                                            created_at=str(message.created_at)))
            self.response.out.write(dict2xml(ret))
        else:
            msglist = []
            for message in messages:
                url = urlparse.urljoin(self.request.uri, urllib.quote(message.guid))
                msglist.append(url)
            self.response.headers["Content-Type"] = 'text/plain'
            self.response.out.write('\n'.join(msglist))


class MessageHandler(webapp.RequestHandler):
    def get(self, guid):
        message = Message.all().filter('guid =', guid).get()
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
        message = Message.all().filter('guid =', guid).get()
        if message:
            if message.status == 'deleted':
                self.response.set_status(410)  # 410 Gone
                self.response.out.write('already deleted')
            else:
                self.response.set_status(409)  # 409 Conflict
                self.response.out.write('already exists')
        else:
            Message.get_or_insert(guid, guid=guid, body=self.request.body, content_type=self.request.headers.get('Content-Type'))
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
