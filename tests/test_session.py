try:
    import unittest2 as unittest
except ImportError:
    import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import requests
import responses

from infoblox import infoblox


class SessionLogging(unittest.TestCase):
    def setUp(self):
        self.p_logger = mock.patch('infoblox.infoblox.logger')
        self.m_logger = self.p_logger.start()
        self.addCleanup(self.p_logger.stop)
        self.session = infoblox.Session()


class SessionWhenConnectionError(SessionLogging):
    @responses.activate
    def setUp(self):
        super(SessionWhenConnectionError, self).setUp()
        responses.add(responses.GET, 'http://www.foo.com',
                      body=requests.ConnectionError(),
                      content_type='application/json')
        try:
            self.session.request('GET', 'http://www.foo.com')
        except Exception as e:
            self.exception = e

    def test_exception_bubbles_up(self):
        self.assertIsInstance(self.exception, requests.ConnectionError)

    def test_exception_logged(self):
        self.m_logger.exception.called_once_with(self.exception)

    def test_log_entry_contains_url(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn("url='http://www.foo.com'", args[0])

    def test_log_entry_contains_method(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn("method='GET'", args[0])

    def test_response_status_is_None(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn('response-status=None', args[0])

    def test_response_content_is_None(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn('response-content=None', args[0])


class SessionWhenHttpError(SessionLogging):
    @responses.activate
    def setUp(self):
        super(SessionWhenHttpError, self).setUp()
        responses.add(responses.GET, 'http://www.foo.com',
                      body='foo-body', status=404,
                      content_type='application/json')
        try:
            self.session.request('GET', 'http://www.foo.com')
        except Exception as e:
            self.exception = e

    def test_exception_bubbles_up(self):
        self.assertIsInstance(self.exception, requests.HTTPError)

    def test_exception_logged(self):
        self.m_logger.exception.called_once_with(self.exception)

    def test_log_entry_contains_url(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn("url='http://www.foo.com'", args[0])

    def test_log_entry_contains_method(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn("method='GET'", args[0])

    def test_log_entry_contains_response_status(self):
        args, __ = self.m_logger.error.call_args
        self.assertIn('response-status=404', args[0])

    def test_log_entry_contains_response_content(self):
        args, __ = self.m_logger.error.call_args
        self.assertTrue("response-content=b'foo-body'" in args[0] or
                        "response-content='foo-body'" in args[0])
