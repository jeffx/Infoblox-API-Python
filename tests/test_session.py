import unittest

from infoblox.session import Session


class TestEndpoint(unittest.TestCase):
    def test_endpoint_property_has_one_trailing_slash_when_url_does_not(self):
        session = Session(url='http://foo.com', version='1.0')
        self.assertEqual(session.endpoint, 'http://foo.com/')
        session.endpoint = 'http://foo.com', '1.0'
        self.assertEqual(session.endpoint, 'http://foo.com/')

    def test_endpoint_property_has_one_trailing_slash_when_url_does(self):
        session = Session(url='http://foo.com/', version='1.0')
        self.assertEqual(session.endpoint, 'http://foo.com/')
        session.endpoint = 'http://foo.com/', '1.0'
        self.assertEqual(session.endpoint, 'http://foo.com/')


class TestUrlize(unittest.TestCase):
    def test_relative_path(self):
        session = Session(url='http://foo.com/api', version='1.0')
        url = session._urlize('some-path')
        self.assertEqual(url, 'http://foo.com/api/some-path')

    def test_absolute_path(self):
        session = Session(url='http://foo.com/api', version='1.0')
        url = session._urlize('/some-path')
        self.assertEqual(url, 'http://foo.com/some-path')


class TestGetMethod(unittest.TestCase):
    def test_get_(self):
        session = Session(url='http://foo.com', version='1.0')
        session.get('relative-path')
