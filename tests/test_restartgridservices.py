import responses
import json

from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestRestartGridServices(testcasefixture.TestCaseWithFixture):
    fixture_name = 'grid_get'

    @classmethod
    def setUpClass(cls):
        super(TestRestartGridServices, cls).setUpClass()
        cls.base_url = 'https://10.10.10.10/wapi/v1.6/'
        cls.ref = json.loads(cls.body)[0]['_ref']
        cls.get_url = ('%sgrid' % cls.base_url)
        cls.post_url = ('%s%s?_function=restartservices' % (cls.base_url, cls.ref))
        cls.payload = {"member_order": "SIMULTANEOUSLY", "service_option": "DHCP"}

    # @responses.activate
    # def test_restart_services(self):
    #     responses.add(responses.GET, self.get_url, body=self.body, status=200)
    #     responses.add(responses.POST, self.post_url, body='[]', status=200)
    #     self.iba_ipa.restart_grid_services(payload=self.payload)

    # @responses.activate
    # def test_host_create_badip(self):
    #     responses.add(responses.GET, self.get_url, body=self.body, status=200)
    #     responses.add(responses.POST, self.post_url, body='\{\}', status=200)
    #     with self.assertRaises(infoblox.InfobloxBadInputParameter):
    #         self.iba_ipa.restart_grid_services(payload=self.payload)

    # @responses.activate
    # def test_host_create_badresponse(self):
    #     responses.add(responses.GET, self.get_url, body=self.body, status=200)
    #     responses.add(responses.POST, self.post_url, body='[]', status=500)
    #     with self.assertRaises(HTTPError):
    #         self.iba_ipa.restart_grid_services(payload=self.payload)
