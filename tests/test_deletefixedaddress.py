import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestDeleteFixedAddress(testcasefixture.TestCaseWithFixture):
    fixture_name = 'fixedaddress_delete'

    @classmethod
    def setUpClass(cls):
        super(TestDeleteFixedAddress, cls).setUpClass()
        cls.delete_url = ('https://10.10.10.10/wapi/v1.6/fixedaddress/'
                          'ZG5zLmZpeGVkX2FkZHJlc3MkMTAuNjMuMTU4Ljc5LjAuLg:192.168.10.1/default')
        cls.get_url = 'https://10.10.10.10/wapi/v1.6/fixedaddress'

    @responses.activate
    def test_host_delete(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=200)
        responses.add(responses.DELETE, self.delete_url, status=200)
        self.ip = self.iba_ipa.delete_fixed_address(
            ipv4addr='192.168.10.1',
            mac='aa:bb:cc:dd:ee:ff',
        )
        self.assertIsNone(self.ip)

    @responses.activate
    def test_host_delete_hostnotfound(self):
        responses.add(responses.GET, self.get_url, body='[]', status=200)
        responses.add(responses.DELETE,
                      self.delete_url,
                      status=200)
        with self.assertRaises(infoblox.InfobloxNotFoundException):
            self.iba_ipa.delete_fixed_address(
                ipv4addr='192.168.10.1',
                mac='aa:bb:cc:dd:ee:ff',
            )

    @responses.activate
    def test_host_delete_servererror(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=500)
        responses.add(responses.DELETE, self.delete_url, status=200)
        with self.assertRaises(HTTPError):
            self.iba_ipa.delete_fixed_address(
                ipv4addr='192.168.10.1',
                mac='aa:bb:cc:dd:ee:ff',
            )
