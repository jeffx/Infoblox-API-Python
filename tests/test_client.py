import unittest

import infoblox


class InfobloxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = infoblox.Client('http://example.com', username='user',
                                     password='foobar', version='2.2',
                                     dns_view='default', network_view='default')


class GetNextAvailableIpTests(InfobloxTest):
    def test_single_returns_list(self):
        result = self.client.get_next_available_ip('10.0.0.1')
        self.assertEqual(result, ['10.0.0.2'])

    def test_multiple_returns_list(self):
        result = self.client.get_next_available_ip('10.0.0.1', count=2)
        self.assertEqual(result, ['10.0.0.2', '10.0.0.3'])


class GetNextAvailableNextworksTests(InfobloxTest):
    def test_single_returns_list(self):
        result = self.client.get_next_available_networks('10.0.0.1')
        self.assertEqual(result, ['10.0.1.0/24'])

    def test_multiple_returns_list(self):
        result = self.client.get_next_available_networks('10.0.0.1', count=2)
        self.assertEqual(result, ['10.0.0.2', '10.0.0.3'])


class HostRecordTests(InfobloxTest):
    def test_create(self):
        host_record = self.client.create_host_record(address='10.0.0.2',
                                                     fqdn='abc.example.com')
        self.assertIn('_ref', host_record)

    def test_get_host_record(self):
        host_record = self.client.get_host_record('abc.example.com')
        self.assertIn('_ref', host_record)
