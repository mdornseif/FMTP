#!/usr/bin/env python
# encoding: utf-8
"""
fmtp-server/acceptance_tests.py

Created by Philipp Benjamin Köppechen on 2011-03-01.
Copyright (c) 2010 HUDORA. All rights reserved.
"""
from datetime import datetime, timedelta
import unittest

from gaetk.webapp2 import WSGIApplication
from webtest import TestApp
from mock import Mock
from huTools import hujson as json

from fmtp_server import Message, MessageHandler, QueueHandler, AdminHandler, db


class DbTestCase(unittest.TestCase):
    """ Basisklasse für TestCases, übernimmt erstellung der Testapp und der db-fixtures"""

    def setUp(self):
        """ Erstellt die Testapp unter self.app, löscht die Fixtures und legt neue aus self.fixtures() an."""
        self.app = TestApp(WSGIApplication([
            ('/admin/([^/]+)/', AdminHandler),
            ('/([^/]+)/', QueueHandler),
            ('/([^/]+)/(.+)/', MessageHandler),
        ], debug=True))

        # clear all Fixtures
        for cls in [Message]:
            db.delete(cls.all())

        db.put(self.fixtures())

    def fixtures(self):
        """Überschreiben, um vor den Tests Datenbankfixtures anzulegen.

        Muss ein Iterable aus db.Model zurückgeben
        """
        return []


class TestMessageHandlerGet(DbTestCase):
    """ Tests der GET-Methode des MessageHandlers.

    Testet, ob die Nachrichten korrekt wiedergegeben werden, bzw korrekte HTTP-Fehler resultieren.
    """

    def fixtures(self):
        """Erstellt Fixture-Messages

        queue somequeue:
            alpha
            deleted (gelöscht)
        queue otherqueue:
            beta
        """
        yield Message(guid='deleted', message_queue_name='somequeue', body='xxx',
                                                         content_type='text/plain', deleted_at=datetime.now())
        yield Message(guid='alpha', message_queue_name='somequeue', body='body', content_type='text/plain')
        yield Message(guid='beta', message_queue_name='someotherqueue', body='body',
                                                                                    content_type='text/plain')

    def test_responds_the_message(self):
        """Nachrichten müssen mit korrektem Inhalt und Mimetype widergegeben werden."""
        response = self.app.get('/somequeue/alpha/')
        self.assertEquals(response.content_type, 'text/plain')
        self.assertEquals(response.body, 'body')

    def test_responds_410_if_message_is_deleted(self):
        """gelöschte Nachrichten dürfen nicht gefunden werden."""
        self.app.get('/somequeue/deleted/', status=410)

    def test_responds_404_if_no_such_message_exists_in_queue(self):
        """Nachrichten aus anderen queues dürfen nicht gefunden werden."""
        # no such guid
        self.app.get('/somequeue/doesnotexist/', status=404)
        # real guid, wrong queue
        self.app.get('/someotherqueue/alpha/', status=404)
        self.app.get('/somequeue/beta/', status=404)

    def test_on_access_gets_called(self):
        """Löst Event aus beim Zugriff"""
        MessageHandler.on_access = Mock()
        self.app.get('/somequeue/alpha/')

        self.assertTrue(MessageHandler.on_access.called)


class TestMessageHandlerDelete(DbTestCase):
    """ Tests der DELETE-Methode des MessageHandlers

    Testet, ob die Nachrichten korrekt gelöscht werden, bzw korrekt HTTP-Fehler resultieren.
    """

    def fixtures(self):
        """Erstellt Fixture-Messages

        queue somequeue:
            killme
        """
        yield Message(guid='killme', body='xxx', content_type='text/plain', message_queue_name='somequeue')

    def test_deletes_the_message(self):
        """Nachrichten müssen korrekt gelöscht werden."""
        self.app.delete('/somequeue/killme/', status=204)

        msg, = Message.all()
        self.assertNotEqual(msg.deleted_at, None)

    def test_responds_404_if_no_such_message_exists(self):
        """Antwortet http-conform, wenn Nachrichten nicht gefunden werden."""
        # no such guid
        self.app.delete('/somequeue/doesnotexist/', status=404)
        # real guid, wrong queue
        self.app.delete('/wronqueue/killme/', status=404)

    def test_responds_410_if_message_is_deleted(self):
        """Antwortet http-conform, wenn Nachrichten schon gelöscht wurden."""
        self.app.delete('/somequeue/killme/')
        self.app.delete('/somequeue/killme/', status=410)

    def test_on_deleted_gets_called(self):
        """Löst Event aus bei erstellung."""
        MessageHandler.on_deleted = Mock()
        self.app.delete('/somequeue/killme/')
        self.assertTrue(MessageHandler.on_deleted.called)

    def test_on_access_gets_called(self):
        """Löst Event aus beim Zugriff"""
        MessageHandler.on_access = Mock()
        self.app.delete('/somequeue/killme/')

        self.assertTrue(MessageHandler.on_access.called)


class TestMessageHandlerPost(DbTestCase):
    """ Tests der POST-Methode des MessageHandlers

    Testet, ob die Nachrichten korrekt angelegt werden, bzw korrekt HTTP-Fehler resultieren.
    """

    def fixtures(self):
        """Erstellt Fixture-Messages

        queue somequeue:
            doesexist
            deleted (gelöscht)
        queue otherqueue:
            new_message
        """
        yield Message(guid='deleted', message_queue_name='somequeue', body='xxx',
                                                         content_type='text/plain', deleted_at=datetime.now())
        yield Message(guid='doesexist', message_queue_name='somequeue', body='body',
                                                                                    content_type='text/plain')
        yield Message(guid='new_message', message_queue_name='otherqueue', body='body',
                                                                                    content_type='text/plain')

    def test_creates_the_message(self):
        """Die Nachricht wird korrekt gespeichert."""
        db.delete(Message.all())  # damit man sie später ohne Annahme per Message.all() finden kann

        self.app.post('/somequeue/new_message/', 'body', {'Content-Type': 'text/plain'})

        msg, = Message.all()
        self.assertEqual(msg.deleted_at, None)
        self.assertEqual(msg.body, 'body')
        self.assertEqual(msg.content_type, 'text/plain')
        self.assertEqual(msg.message_queue_name, 'somequeue')

    def test_allows_same_guid_in_different_queues(self):
        """In verschiedenen Queues können Nachrichten die gleichen guid haben."""
        self.app.post('/alpha/new_message/', 'body', {'Content-Type': 'text/plain'})
        self.app.post('/beta/new_message/', 'body', {'Content-Type': 'text/plain'})

    def test_responds_409_when_created_twice(self):
        """Antwortet http-conform, wenn Nachrichten schon existieren."""
        self.app.post('/somequeue/doesexist/', 'body', {'Content-Type': 'text/plain'}, status=409)

    def test_responds_410_when_overwriting_deleted(self):
        """Antwortet http-conform, wenn bereits gelöschte Nachrichten existieren."""
        self.app.post('/somequeue/deleted/', 'body', {'Content-Type': 'text/plain'}, status=410)

    def test_denies_creation_in_disallowed_message_queue(self):
        """Antwortet http-conform auf den Versuch, eine Nachricht in eine verbotene Queue zu Posten."""
        MessageHandler.check_messagequeue_name = lambda self, name: name != 'illegalqueue'

        self.app.post('/illegalqueue/new_message/', 'body', {'Content-Type': 'text/plain'}, status=403)

    def test_denies_creation_with_disallowed_guid(self):
        """Antwortet http-conform auf den Versuch, eine Nachricht mit ungültiger Queue zu Posten."""
        self.app.post('/somequeue/***/', 'body', {'Content-Type': 'text/plain'}, status=403)

    def test_on_created_gets_called(self):
        """Löst Event aus bei erstellung."""
        MessageHandler.on_created = Mock()
        self.app.post('/somequeue/new_message/', 'body', {'Content-Type': 'text/plain'})
        self.assertTrue(MessageHandler.on_created.called)

    def test_on_access_gets_called(self):
        """Löst Event aus beim Zugriff"""
        MessageHandler.on_access = Mock()
        self.app.post('/somequeue/new_message/', 'body', {'Content-Type': 'text/plain'})

        self.assertTrue(MessageHandler.on_access.called)


class TestQueueHandlerGet(DbTestCase):
    """ Tests der GET-Methode des QueueHandlers.

    Testet, ob die Nachrichtenlisten korrekt widergebenen werden.
    """

    def fixtures(self):
        """Erstellt Fixture-Messages

        queue alpha:
            alice
            deleted (gelöscht)
        queue beta:
            bob
        """
        yield Message(guid='deleted', message_queue_name='alpha', body='deleted',
                                                         content_type='text/plain', deleted_at=datetime.now())
        yield Message(guid='alice', message_queue_name='alpha', body='body', content_type='text/plain')
        yield Message(guid='bob', message_queue_name='beta', body='body', content_type='text/plain')

    def get_json(self, path):
        """Stellt eine GET-Anfrage an path und konvertiert das Ergebnis nach JSON."""
        result = self.app.get(path, headers={'Accept': 'application/json'})
        return json.loads(result.body)

    def get_message_urls(self, path):
        """Extrahiert die URLS der Nachrichten aus einer JSON-anfrage an path"""
        return [msg['url'] for msg in self.get_json(path)['messages']]

    def test_shows_correct_message_url(self):
        """Es werden nur die Nachrichten aus der eigenen queue, die ungelöscht sind, angezeigt."""
        self.assertEquals(['http://localhost/alpha/alice/'], self.get_message_urls('/alpha/'))
        self.assertEquals(['http://localhost/beta/bob/'], self.get_message_urls('/beta/'))

    def test_delivers_plaintext(self):
        """Nachrichtenlisten können als Plaintext abgefragt werden."""
        result = self.app.get('/alpha/', headers={'Accept': 'text/plain'})
        self.assertEquals(['http://localhost/alpha/alice/'], result.body.splitlines())

    def test_delivers_json(self):
        """Nachrichtenlisten können als JSON abgefragt werden."""
        self.get_json('/alice/')

    def test_delivers_xml(self):
        """Nachrichtenlisten können als XML abgefragt werden."""
        result = self.app.get('/alpha/', headers={'Accept': 'application/xml'})
        self.assertTrue(result.body.startswith('<'))
        self.assertTrue(result.body.endswith('>'))
        self.assertTrue('<messages>' in result.body)
        self.assertTrue('<message>' in result.body)
        self.assertTrue('http://localhost/alpha/alice' in result.body)

    def test_on_access_gets_called(self):
        """Das Event on_access wird aufgerufen."""
        QueueHandler.on_access = Mock()
        self.app.get('/somequeue/')

        QueueHandler.on_access.assert_called_with('somequeue')


class TestAdminHandlerDelete(DbTestCase):
    """ Tests der DELETE-Methode des AdminHandlers.

    Die methode löst die GarbageCollection der Queue aus.
    Testet, ob es die richtigen Nachrichen löscht.
    """
    def fixtures(self):
        young = datetime.now() - timedelta(days=2)
        old = datetime.now() - timedelta(days=7, hours=2)

        yield Message(guid='oldenough', message_queue_name='alpha', deleted_at=old,
                                                                       body='body', content_type='text/plain')
        yield Message(guid='tooyoung', message_queue_name='alpha', deleted_at=young,
                                                                       body='body', content_type='text/plain')
        yield Message(guid='wrongqueue', message_queue_name='beta', deleted_at=old,
                                                                       body='body', content_type='text/plain')
        yield Message(guid='notdeleted', message_queue_name='beta', deleted_at=None,
                                                                       body='body', content_type='text/plain')

    def test_collects_old_deleted_message_in_given_queue(self):
        """Nachrichten, die vor der Aufbewahrungsfrist gelöscht wurden, werden garbagecollected."""
        self.app.delete('/admin/alpha/')
        self.assertFalse(self._message_exists('oldenough'))

    def test_doesnt_collect_young_messages(self):
        """Nachrichten, die in der Aufbewahrungsfrist liegen, werden nicht garbagecollected."""
        self.app.delete('/admin/alpha/')
        self.assertTrue(self._message_exists('tooyoung'))

    def test_doesnt_collect_messages_in_other_queues(self):
        """Nachrichten aus fremden Queues werden nicht garbagecollected."""
        self.app.delete('/admin/alpha/')
        self.assertTrue(self._message_exists('wrongqueue'))

    def test_doesnt_collect_undeleted_messages(self):
        """Nachrichten, die nicht gelöscht sind, werden nicht garbagecollected."""
        self.app.delete('/admin/alpha/')
        self.assertTrue(self._message_exists('notdeleted'))

    def test_on_access_gets_called(self):
        """Das Event on_access wird aufgerufen."""
        AdminHandler.on_access = Mock()
        self.app.delete('/admin/somequeue/')
        AdminHandler.on_access.assert_called_with('somequeue')

    def test_answers_report(self):
        """Bei Erfolg wird eine json-zusammenfassung geliefert."""
        result = self.app.delete('/admin/alpha/')
        self.assertEquals(json.loads(result.body), {
            'success': True,
            'deleted': 1,
        })

    def _message_exists(self, guid):
        """Helper, um festzustellen, ob eine Nachricht existiert."""
        return bool(Message.all().filter('guid =', guid).fetch(1))


class TestAdminHandlerGet(DbTestCase):
    """Tests der GET-Methode des AdminHandlers.

    Testet, ob die erweiterten Nachrichtenlisten korrekt widergegeben werden.
    """

    def fixtures(self):
        """Erstellt Fixture-Messages

        queue alpha:
            alice
            deleted (gelöscht)
        queue beta:
            bob
        """
        self.date = datetime(2011, 3, 23)

        yield Message(guid='deleted', message_queue_name='alpha', body='deleted', content_type='text/plain',
                                                                   created_at=self.date, deleted_at=self.date)
        yield Message(guid='alice', message_queue_name='alpha', body='body', content_type='text/plain', created_at=self.date)
        yield Message(guid='bob', message_queue_name='beta', body='body', content_type='text/plain', created_at=self.date)

    def test_returns_correct_list(self):
        result = self.app.get('/admin/alpha/')

        body = json.loads(result.body)

        self.assertEqual(body['messages'], [
                {
                    u'queue': u'alpha',
                    u'guid': u'deleted',
                    u'is_deleted': True,
                    u'created_at': u'2011-03-23 00:00:00',
                    u'deleted_at': u'2011-03-23 00:00:00',
                    u'content_type': u'text/plain',
                }, {
                    u'queue': u'alpha',
                    u'guid': u'alice',
                    u'is_deleted': False,
                    u'created_at': u'2011-03-23 00:00:00',
                    u'deleted_at': None,
                    u'content_type': u'text/plain',
                }
            ]
        )

    def test_on_access_gets_called(self):
        """Das Event on_access wird aufgerufen."""
        AdminHandler.on_access = Mock()
        self.app.get('/admin/somequeue/')

        AdminHandler.on_access.assert_called_with('somequeue')
