#!/usr/bin/env python
# encoding: utf-8
"""
fmtp-server/main.py

Created by Maximillian Dornseif on 2010-11-16.
Copyright (c) 2010 HUDORA. All rights reserved.
"""

from datetime import datetime, timedelta
import re

from huTools import hujson as json
from huTools.structured import dict2xml
from huTools.http.tools import quote
from google.appengine.ext import db
from gaetk.handler import BasicHandler, JsonResponseHandler
from gaetk.handler import HTTP404_NotFound, HTTP401_Unauthorized, HTTP403_Forbidden, HTTP410_Gone, HTTP409_Conflict


class Message(db.Model):
    """Repräsentiert eine FMTP-Nachricht."""
    guid = db.StringProperty(required=True)
    message_queue_name = db.StringProperty(required=True)
    content_type = db.StringProperty(required=True)
    body = db.BlobProperty(required=True)
    deleted_at = db.DateTimeProperty()  # None, wenn die Nachricht nicht gelöscht wurde, sonst das datum der Löschung.
    created_at = db.DateTimeProperty(auto_now_add=True)


class QueueHandler(BasicHandler):
    """Handler für FMTP-Nachrichtenlisten, gemäss README/Listenformate.

    Der Handler kümmert sich um die Auflistung der Nachrichten in einer Queue in verschiedenen Formaten (GET),
    und um Garbage Collection (DELETE).

    Dieser Handler ist als Basisklasse vorgesehen, in dessen Erben zur Anpassung

     * (min/max)_retry_interval,
     * max_messages, und
     * on_access

    überschrieben werden können (siehe dort zur wozu).
    """

    # Zeitspanne in Millisekunden, die ein Client mindestens warten MUSS, bevor er eine neue Anfrage stellt.
    min_retry_interval = 500

    # Zeitspanne in Millisekunden, die ein Client höchstens warten sollte, bevor er eine neue Anfrage stellt.
    max_retry_interval = 60000

    # Maximale Anzahl von Nachrichten, die angezeigt werden
    max_messages = 10

    def _message_as_dict(self, message):
        """Erstellt ein dict, das eine Nachricht in der Liste repräsentiert."""
        return {
            'url': '%s/%s/' % (self.request.uri.rstrip('/'), quote(message.guid)),
            'created_at': str(message.created_at),
        }

    def on_access(self, message_queue_name):
        """Event, das beim Versuch, eine Messagequeue abzufragen ausgelöst wird.
        message_queue_name ist der Parameter aus der URL.

        Um den Zugriff auf Messagequeues zu kontrollieren, kann ggf. HTTP401_Unauthorized
        geraised werden.
        """
        pass

    def get(self, message_queue_name):
        """ Liefert eine Übersicht über die Nachrichten in der Queue zurück.

        Kann in JSON, XML, oder plaintext abgefragt werden.
        Für eine Beschreibung des Formats siehe README.
        """
        self.on_access(message_queue_name)
        messages = (Message.all()
                           .filter('message_queue_name =', message_queue_name)
                           .filter('deleted_at =', None)
                           .order('created_at')
                           .fetch(self.max_messages))

        document = {
            'min_retry_interval': self.min_retry_interval,
            'max_retry_interval': self.max_retry_interval,
            'messages': [self._message_as_dict(msg) for msg in messages],
        }

        accept = self.request.headers.get('Accept', '')

        if accept.startswith('application/json'):
            self.response.headers["Content-Type"] = 'application/json'
            self.response.out.write(json.dumps(document))
        elif accept.startswith('application/xml'):
            self.response.headers["Content-Type"] = 'application/xml'
            self.response.out.write(dict2xml(document, listnames={'messages': 'message'}))
        else:
            self.response.headers["Content-Type"] = 'text/plain'
            self.response.out.write('\n'.join(x['url'] for x in document['messages']))


class MessageHandler(BasicHandler):
    """Handler für individuelle Messages.

    Dieser Handler ist als Basisklasse vorgesehen, in dessen Erben zur Anpassung

    * on_access,
    * on_created, und
    * on_deleted
    * check_messagequeue_name


    überschreiben werden können (siehe dort zur wozu).
    """

    # Regulärer Ausdruck, dem die guids der Nachrichten entsprechen müssen
    guid_pattern = r'^[a-zA-Z0-9_-]+$'

    def _find_message(self, message_queue_name, guid):
        """Gibt die message_queue_name und guid entsprechene Nachricht aus der DB zurück,
        oder None, wenn keine solche existiert."""
        return (Message.all()
                       .filter('guid =', guid)
                       .filter('message_queue_name', message_queue_name)
                       .get())

    def check_messagequeue_name(self, message_queue_name):
        """Gibt True zurück, wenn message_queue_name ein erlaubter Name für eine MesssageQueue ist.
        Per default sind alle Namen erlaubt.

        Kann zur Anpassung überschrieben werden, z.B:

        def is_allowed_message_queue_name(self, message_queue_name):
            return message_queue_name in ['queue_a', 'queue_b']
        """
        return True

    def on_access(self, method, message_queue_name, guid, message):
        """Event, das beim Versuch, auf eine Nachricht zuzugreifen ausgelöst wird.
        method ist die HTTP-methode, message_queue_name und guid sind die Parameter
        aus der URL, message die Nachricht oder None, wenn keine gefunden wurde.

        Um den Zugriff auf Nachrichten zu kontrollieren, kann ggf. HTTP401_Unauthorized
        geraised werden.
        """
        pass

    def on_created(self, message):
        """Event nach der Nachrichtenerstellung, z.B. für Auditlogs"""
        pass

    def on_deleted(self, message):
        """Event nach der Nachrichtenlöschung, z.B. für AuditLogs"""
        pass

    def get(self, message_queue_name, guid):
        """Gibt die Nachricht aus der gegebenen queue mit der gegebeben guid.
        Der Content-Type ist dabei der bei der Erstellung angegebene.

        Mögliche Antworten sind:
        - 200 Ok, wenn die entsprechende Nachricht gefunden wurde,
        - 404 Not Found, wenn die Nachricht nicht gefunden wurde,
        - 410 Gone, wenn eine entsprechende Nachricht existierte, aber gelöscht wurde.
        """
        message = self._find_message(message_queue_name, guid)
        self.on_access('GET', message_queue_name, guid, message)
        if not message:
            raise HTTP404_NotFound('Es existiert keine Nachricht mit guid %r in der Queue %r.'
                                                                                % (guid, message_queue_name))
        if message.deleted_at:
            raise HTTP410_Gone('Nachricht mit guid %r in der Queue %r wurde bereits am %s geloescht.'
                                                             % (guid, message_queue_name, message.deleted_at))
        if message.content_type:
            self.response.headers["Content-Type"] = message.content_type.encode('utf-8')
        else:
            self.response.headers["Content-Type"] = 'application/octet-stream'
        self.response.out.write(message.body)

    def post(self, message_queue_name, guid):
        """Erstellt eine Nachricht in der gegebenen queue mit der gegebenen guid.
        Bei der Erstellung wird der header 'Content-Type' beachtet.

        Mögliche Antworten sind:
        - 204 No Content, wenn die Nachricht erstellt wurde, TODO: warum nicht 201?
        - 409 Conflict, wenn eine Nachricht mit der guid schon existiert,
        - 410 Gone, wenn eine Nachricht mit der guid schon existierte, aber gelöscht wurde.
        """
        message = self._find_message(message_queue_name, guid)
        self.on_access('POST', message_queue_name, guid, message)

        if not self.check_messagequeue_name(message_queue_name):
            raise HTTP403_Forbidden('Ungueltiger queue-name: %r' % message_queue_name)

        if not re.match(self.guid_pattern, guid):
            raise HTTP403_Forbidden('Ungueltige guid: %r. guids muessen %r matchen.'
                                                                                  % (guid, self.guid_pattern))
        if message:
            if message.deleted_at:
                raise HTTP410_Gone('Nachricht mit guid %r in der Queue %r wurde bereits am %s geloescht.'
                                                             % (guid, message_queue_name, message.deleted_at))
            else:
                raise HTTP409_Conflict('Es existiert bereits eine Nachricht mit guid %r in der Queue %r.'
                                                                                % (guid, message_queue_name))
        message = Message.get_or_insert('%s/%s' % (message_queue_name, guid),
                                        guid=guid,
                                        body=self.request.body,
                                        message_queue_name=message_queue_name,
                                        content_type=self.request.headers.get('Content-Type'),
                                        deleted_at=None)
        self.on_created(message)
        self.response.set_status(201)

    def delete(self, message_queue_name, guid):
        """Löscht die Nachricht mit der gegebenen guid in der gegebenen queue.
        Mögliche Antworten sind:
        - 204 No Content, wenn die Nachricht gelöscht wurde,
        - 404 Not Found, wenn keine Nachricht mit der gegebenen guid in der queue gefunden wurde,
        - 410 Gone, wenn eine entsprechende Nachricht existierte, aber bereits gelöscht wurde.
        """
        message = self._find_message(message_queue_name, guid)
        self.on_access('DELETE', message_queue_name, guid, message)
        if not message:
            raise HTTP404_NotFound('Es existiert keine Nachricht mit guid %r in der Queue %r.'
                                                                                % (guid, message_queue_name))
        if message.deleted_at:
            raise HTTP410_Gone('Nachricht mit guid %r in der Queue %r wurde bereits am %s geloescht.'
                                                             % (guid, message_queue_name, message.deleted_at))
        message.deleted_at = datetime.now()
        message.put()
        self.on_deleted(message)

        del self.response.headers['Content-Type']
        self.response.set_status(204)  # no content


class AdminHandler(JsonResponseHandler):
    """Handler für die Administrative sicht auf eine MessageQueue.

    Dieser Handler ist als Basisklasse vorgesehen, in dessen Erben zur Anpassung

    * on_access,
    * max_messages
    * retention_period_days

    überschreiben werden können (siehe dort zur wozu).
    """

    # Maximale Anzahl von Nachrichten, die angezeigt werden
    max_messages = 1000

    # Minimale Zeit in Tagen, die die gelöschten Nachrichten aufbewahrt werden sollen (also nicht garbage
    # collected werden dürfen)
    retention_period_days = 7

    def get(self, message_queue_name):
        """Gibt eine Liste von [max_messages] zusammenfassungen von Nachrichten wieder.

        Dabei werden auch gelöschte Nachrichten angezeigt.
        """
        self.on_access(message_queue_name)
        messages = Message.all().filter('message_queue_name =', message_queue_name)
        return self.paginate(messages, self.max_messages, datanodename='messages',
                                                          formatter=self._message_as_dict)

    def delete(self, message_queue_name):
        """ Garbagecollected Nachrichten in der angegebenen Queue.

        Löst das Ereignis on_access aus, und löscht alle Nachrichten, die vor nicht weniger als
        `retention_period_days` Tagen als gelöscht markiert wurden (siehe `MessageHandler.delete`)
        """
        self.on_access(message_queue_name)

        delete_before = datetime.now() - timedelta(days=self.retention_period_days)
        messages = (Message.all()
                           .filter('message_queue_name = ', message_queue_name)
                           .filter('deleted_at !=', None)
                           .filter('deleted_at <', delete_before))

        collected = messages.count()
        db.delete(messages)

        return {
            'success': True,
            'deleted': collected,
        }

    def on_access(self, message_queue_name):
        """Event, das beim Versuch, eine Messagequeue abzufragen ausgelöst wird.
        message_queue_name ist der Parameter aus der URL.

        Um den Zugriff zu kontrollieren, kann ggf. HTTP401_Unauthorized
        geraised werden.
        """
        pass

    def _message_as_dict(self, message):
        """Formatiert eine message als JSON"""
        return {
            'guid': message.guid,
            'queue': message.message_queue_name,
            'is_deleted': bool(message.deleted_at),
            'created_at': message.created_at,
            'deleted_at': message.deleted_at,
            'content_type': message.content_type,
        }
