import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestGetFixedAddress(testcasefixture.TestCaseWithFixture):
    fixture_name = 'fixedaddress_get'

    @classmethod
    def setUpClass(cls):
        super(TestGetFixedAddress, cls).setUpClass()
        cls.get_url = 'https://10.10.10.10/wapi/v1.6/fixedaddress'

    @responses.activate
    def test_get_fixed_address_includes_ipv4addr(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=200)
        self.r_json = self.iba_ipa.get_fixed_address(
            ipv4addr='192.168.10.1',
            mac='aa:bb:cc:dd:ee:ff',
        )
        self.assertEqual(self.r_json[0]['ipv4addr'], '192.168.10.1')

    @responses.activate
    def test_get_fixed_address_bad_network(self):
        responses.add(responses.GET, self.get_url, body='[]', status=200)
        with self.assertRaises(infoblox.InfobloxNotFoundException):
            self.iba_ipa.get_fixed_address(
                ipv4addr='192.168.10.10',
                mac='aa:bb:cc:dd:ee:ff',
            )

    @responses.activate
    def test_get_fixed_address_badresponse(self):
        responses.add(responses.GET, self.get_url, body='[]', status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.get_fixed_address(
                ipv4addr='192.168.10.1',
                mac='aa:bb:cc:dd:ee:ff',
            )
