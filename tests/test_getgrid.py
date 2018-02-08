import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestGetGrid(testcasefixture.TestCaseWithFixture):
    fixture_name = 'grid_get'

    @classmethod
    def setUpClass(cls):
        super(TestGetGrid, cls).setUpClass()
        cls.get_url = 'https://10.10.10.10/wapi/v1.6/grid'

    @responses.activate
    def test_get_grid_includes_GridMember_name(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=200)
        self.r_json = self.iba_ipa.get_grid()
        self.assertIn('GridMember', self.r_json[0]['_ref'])

    @responses.activate
    def test_get_grid_bad_network(self):
        responses.add(responses.GET, self.get_url, body='[]', status=200)
        with self.assertRaises(infoblox.InfobloxNotFoundException):
            self.iba_ipa.get_grid(name='FakeGrid')

    @responses.activate
    def test_get_grid_badresponse(self):
        responses.add(responses.GET, self.get_url, body='[]', status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.get_grid()
