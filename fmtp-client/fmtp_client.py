# coding: utf-8
"""
fmtp_client.py - Basic FMTP Client library

Created by Philipp Benjamin Köppchen on 2011-03-07.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.


Benutzungsbeispiele:

Einrichtung per Server

>>> myserver = Server('http:///fmtp.example.com', credentials='someone@example.com:topsecret')
>>> myqueue = myserver['myqueue']

Einrichtung per Queue

>>> myqueue = Queue('http://fmtp.example.com/myqueue/', credentials='someone@example.com:topsecret')

Nachricht senden:

>>> myqueue.post_message('123123', 'text/plain', 'this is a message')

Nachrichten abrufen und bestätigen (löschen):

>>> for message in myqueue:
>>>    print message.content
>>>    message.acknowledge()

"""

from urlparse import urljoin
from huTools import hujson, http


class FmtpError(RuntimeError):
    """Basisklasse für Ftmp-spezifische Fehler"""
    pass


class FmtpMessageDeleted(FmtpError):
    """Diese Exception wird geworfen, wenn eine bereits gelöschte Nachricht behandelt werden soll."""
    pass


class FmtpMessageExists(FmtpError):
    """Diese Exception wird geworfen, wenn eine bereits existierende Nachricht angelegt werden soll."""
    pass


class FmtpFormatError(FmtpError):
    """Diese Exception wird geworfen, wenn die Antworten des Servers nicht verstanden werden."""
    pass


class FmtpHttpError(FmtpError):
    """Diese Exception wird geworfen, wenn ein unerwarteter HTTP-Statuscode auftritt"""


class Server(object):
    """Schnittstelle zu einem FMTP-Server.

    Ein Server startet HTTP-Verbindungen nur 'on demand', es ist daher sicher, Server in einer Konfigurations-
    oder Environmentdatei als Singletons zu erstellen und später zu nutzen.

    Sofern man nur Queues hat, deren Namen zur Programmierzeit bekannt sind, ist die benutzung von Queue zu
    bevorzugen.
    """

    def __init__(self, url, credentials=None):
        """Instantiiert die Schnittstelle

        url: Basisurl, unterhalb derer sich die FMTP-queues befinden (z.B. http://example.com, wenn
             http://example.com/q eine queue ist)
        credetials: HTTP-Credetials in der form username:password
        """
        self.url = url
        self.credentials = credentials

    def __getitem__(self, key):
        """Gibt eine Queue auf dem Server mit dem gegebenen Namen zurück."""
        # url immer immer mit trailing slash
        url = urljoin(self.url, key).rstrip('/') + '/'
        return Queue(url, self.credentials)


class Queue(object):
    """Schnittstelle zu FMTP-Queues.

    Eine Queue startet HTTP-Verbindungen nur 'on demand', es ist daher sicher, Queues in einer Konfigurations-
    oder Environmentdatei als Singletons zu erstellen und später zu nutzen.
    """

    def __init__(self, queue_url, credentials=None):
        """Instantiiert die Queue-Schnittstelle.

        queue_url: ist die URL des QueueHandlers (siehe fmtp_server)
        credetials: HTTP-Credetials in der form username:password
        """
        self.queue_url = queue_url
        self.credentials = credentials

    def __iter__(self):
        """Iteriert über die Nachrichten auf der Queue.

        Ruft zuerst die Nachrichtenübersicht ab, und dann schrittweise die einzelnen Nachrichten, und gibt
        diese als Message wieder.

        Mögliche Exceptions sind FmtpFormatError und FmtpHttpError
        """
        for url in self._fetch_message_urls():
            yield self._fetch_message(url)

    def post_message(self, guid, content_type, content):
        """Veröffentlicht eine Nachricht auf der FMTP-Queue.

        guid: Eindeutiger Bezeichner für die Nachricht
        content_type: Content-Type der Nachricht, beispielsweise text/plain
        content: Inhalt der Nachricht
        """
        url = self.queue_url + guid + '/'
        headers = {'Content-Type': content_type}

        status, headers, body = http.fetch(url, method='POST', credentials=self.credentials, headers=headers,
                                                                                              content=content)
        if status == 409:
            raise FmtpMessageExists('Message %s already exists' % url)
        elif status == 410:
            raise FmtpMessageDeleted('Message %s is deleted' % url)
        elif status != 201:
            raise FmtpHttpError('expected 201 when posting to %s, got %s' % (url, status))

    def _fetch_message_urls(self):
        """Erfragt die URLs der Nachrichten auf der Queue vom Server, und gibt sie als Liste zurück.

        Mögliche Exceptions: FmtpHttpError, FmtpFormatError
        """
        status, headers, body = http.fetch(self.queue_url, method='GET', credentials=self.credentials,
                                                                       headers={'Accept': 'application/json'})
        # Nach HTTP-Fehlern schauen.
        if status != 200:
            raise FmtpHttpError('requested %s as Messagelist, got %s' % (self.queue_url, status))

        # Antwort parsen, wenn nicht parsebar, exception
        try:
            data = hujson.loads(body)
        except:
            raise FmtpFormatError('Expeceted to get a json messagelist at %s.' % self.queue_url)

        # Urls auflisten, wenn Format nicht stimmt: exception
        try:
            return [msg['url'] for msg in data['messages']]
        except KeyError:
            raise FmtpFormatError('Expected the message at %s list to have /messages[*]/url', self.queue_url)

    def _fetch_message(self, url):
        """Erfragt eine Nachricht von der Queue, und gibt sie als Message zurück.

        Mögliche Exceptions: FmtpHttpError, FmtpFormatError
        """
        status, headers, body = http.fetch(url, method='GET', credentials=self.credentials)
        if status != 200:
            raise FmtpHttpError('expected 200 when fetching %s, got %s' % (url, status))

        return Message(self, url, headers['content-type'], body)

    def _acknowledge_message(self, url):
        """Bestätigt den Empfang einer Nachricht, und löscht sie von der Queue.

        url: die Url der Nachricht

        Mögliche Exceptions: FmtpMessageDeleted, FmtpHttpError

        Diese Funktion sollte nicht direkt aufgerufen werden.
        """
        status, headers, body = http.fetch(url, method='DELETE', credentials=self.credentials,
                                                                       headers={'Accept': 'application/json'})
        if status == 410:
            raise FmtpMessageDeleted('Message %s already deleted' % url)
        if status != 204:
            raise FmtpHttpError('expected 204 when deleting %s, got %s' % (url, status))


class Message(object):
    """Eine Nachricht auf einem Fmtp-Queue.

    Auf den Inhalt kann über content/content-type zugegriffen werden, sobald die Bearbeitung abgeschlossen
    ist, muss die Nachricht per .ackowlege gelöscht werden.
    """

    def __init__(self, queue, url, content_type, content):
        """Instantiiert eine Nachricht.

        queue: das Queue-object, von dem die Nachricht stammt.
        url: die Url unter der die Nachricht abgerufen wurde.
        content_type: Content-Type der Nachricht, z.B. text/plain
        content: Inhalt der Nachricht

        Nachrichten sollten nicht direkt initialisiert werden.
        """
        self.queue = queue
        self.url = url
        self.content_type = content_type
        self.content = content

    def acknowledge(self):
        """Bestätigt die verarbeitung der Nachricht, und löscht sie vom Server.

        Mögliche Exceptions: FmtpHttpError, FmtpMessageDeleted
        """
        self.queue._acknowledge_message(self.url)

    def __repr__(self):
        """Debugdarstellung der Nachricht."""
        return '<Message url=%s, content_type=%s>' % (self.url, self.content_type)
