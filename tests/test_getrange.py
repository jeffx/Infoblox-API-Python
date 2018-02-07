import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestGetRange(testcasefixture.TestCaseWithFixture):
    fixture_name = 'range_get'

    @classmethod
    def setUpClass(cls):
        super(TestGetRange, cls).setUpClass()
        with responses.RequestsMock() as res:
            res.add(responses.GET,
                    'https://10.10.10.10/wapi/v1.6/range',
                    body=cls.body,
                    status=200)
            cls.r_json = cls.iba_ipa.get_range(
                network='192.168.10.0/24',
                fields='member,start_addr,end_addr')

    def test_get_range_includes_start_addr(self):
        self.assertEqual(self.r_json[0]['start_addr'], '192.168.10.21')

    def test_get_range_includes_end_addr(self):
        self.assertEqual(self.r_json[0]['end_addr'], '192.168.10.254')

    def test_get_range_includes_grid_member(self):
        self.assertEqual(self.r_json[0]['member']['name'], 'grid.domain.com')

    @responses.activate
    def test_get_range_bad_network(self):
        responses.add(responses.GET,
                      'https://10.10.10.10/wapi/v1.6/range',
                      body='[]',
                      status=200)
        with self.assertRaises(infoblox.InfobloxNotFoundException):
            self.iba_ipa.get_range(network='not.a.network')

    @responses.activate
    def test_get_range_badresponse(self):
        responses.add(responses.GET,
                      'https://10.10.10.10/wapi/v1.6/range',
                      body='[]',
                      status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.get_range(network='192.168.10.0/24')
