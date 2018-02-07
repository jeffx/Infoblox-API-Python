import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestGetLease(testcasefixture.TestCaseWithFixture):
    fixture_name = 'lease_get'

    @classmethod
    def setUpClass(cls):
        super(TestGetLease, cls).setUpClass()
        cls.get_url = 'https://10.10.10.10/wapi/v1.6/lease'
        cls.query_params = {'address': '192.168.1.10'}

    @responses.activate
    def test_get_lease(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=200)
        self.lease = self.iba_ipa.get_lease(query_params=self.query_params)
        self.assertListEqual(self.lease, [])

    @responses.activate
    def test_get_ip_by_hostnotfound(self):
        responses.add(responses.GET, self.get_url, body='[]', status=200)
        with self.assertRaises(infoblox.InfobloxNotFoundException):
            self.iba_ipa.get_lease(query_params=self.query_params)

    @responses.activate
    def test_get_ip_by_host_serverfail(self):
        responses.add(responses.GET, self.get_url, body='[]', status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.get_lease(query_params=self.query_params)
