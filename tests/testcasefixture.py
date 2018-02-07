import os
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from infoblox import infoblox


class TestCaseWithFixture(unittest.TestCase):
    location = os.path.dirname(__file__)
    fixture_name = None

    @classmethod
    def setUpClass(cls):
        super(TestCaseWithFixture, cls).setUpClass()
        if cls.fixture_name is not None:
            cls.body = cls.load_fixture(cls.fixture_name)
        cls.iba_ipa = infoblox.Infoblox('10.10.10.10', 'foo', 'bar',
                                        '1.6', 'default', 'default')

    @classmethod
    def load_fixture(cls, fixture_name):
        filename = "{0}/data/{1}.json".format(cls.location, cls.fixture_name)
        with open(filename, 'r') as file:
            return file.read()
