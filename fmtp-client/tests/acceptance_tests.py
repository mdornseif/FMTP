# coding: utf-8
"""
tests.py - Testing the FMTP Client library

Created by Philipp Benjamin Köppchen on 2011-03-07.
Copyright (c) 2010, 2011 HUDORA. All rights reserved.
"""

import unittest
import fmtp_client
import mock


class TestServer(unittest.TestCase):
    """Testet die Queueinstantiierung per Server"""

    def setUp(self):
        self.server = fmtp_client.Server('http://example.com', credentials='victoria:secret')
        self.queue = self.server['chat']

    def test_has_correct_url(self):
        """Überprüft, ob die url der Queue korrekt ist."""
        self.assertEquals(self.queue.queue_url, 'http://example.com/chat/')

    def test_has_correct_creds(self):
        """Überprüft, ob die Credentials korrekt sind."""
        self.assertEquals(self.queue.credentials, 'victoria:secret')


class TestMessagePosting(unittest.TestCase):
    """Testet das Posten einer Nachricht auf einem FMTP-Queue.

    Http-Communikation wird dabei gemocked."""

    def setUp(self):
        self.queue = fmtp_client.Queue('http://example.com/chat/')
        # keine echten HTTP-verbindungen zum testen
        self.fetch = fmtp_client.http.fetch = mock.Mock()

    def test_successfull_post_message(self):
        """ Ein erfolgreiches post_message führt POST http://example.com/queue/guid aus."""
        self.fetch.return_value = (201, {}, '')

        self.queue.post_message('1', 'text/plain', 'Hi Alice')

        self.fetch.assert_called_with('http://example.com/chat/1/', method='POST', content='Hi Alice',
                                                     headers={'Content-Type': 'text/plain'}, credentials=None)

    def test_posting_over_existing_message(self):
        """Der Versuch, eine existierende Nachricht erneut zu Posten, führt zu FtmpMessageExsists."""
        self.fetch.return_value = (409, {}, '')
        self.assertRaises(fmtp_client.FmtpMessageExists, self.queue.post_message, '1', 'text/plain',
                                                                                           'Do it again, sam')

    def test_posting_over_deleted_message(self):
        """Der Versuch, eine bereits gelöschte Nachricht erneut zu Posten, führt zu FtmpMessageExsists."""
        self.fetch.return_value = (410, {}, '')
        self.assertRaises(fmtp_client.FmtpMessageDeleted, self.queue.post_message, '1', 'text/plain',
                                                                                         'Afterlife is scary')


class TestReceivingMessages(unittest.TestCase):
    """Testet das Abrufen einer Nachricht von einem FMTP-Queue.

    Http-Communikation wird dabei gemocked."""

    def setUp(self):
        self.queue = fmtp_client.Queue('http://example.com/chat/')
        fmtp_client.http.fetch = self.mock_fetch

    def test_successful_iteration(self):
        """Testet eine erfolgreiche Iteration über die Nachrichten auf einer Queue.

        Eine erfolgreiche Iteration erfragt zunächst vom Server die Liste der Nachrichten, und dann die
        einzelnen Nachrichten."""

        # Antworten von Fetch festlegen
        self.http_responses = [
            (200, {}, '{"messages": [{"url": "http://example.com/chat/1/"},'
                                    '{"url": "http://example.com/chat/2/"}]}'),
            (200, {'content-type': 'text/plain'}, 'Hi Alice'),
            (200, {'content-type': 'text/plain'}, 'Hi Bob'),
        ]

        # nachrichten abrufen
        messages = list(self.queue)

        self.assertEquals(messages[0].content, 'Hi Alice')
        self.assertEquals(messages[0].content_type, 'text/plain')

        self.assertEquals(messages[1].content, 'Hi Bob')
        self.assertEquals(messages[0].content_type, 'text/plain')

    def mock_fetch(self, *args, **kwargs):
        """Simulation von huTools.http.fetch"""
        return self.http_responses.pop(0)
