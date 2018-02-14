import responses
from requests.exceptions import HTTPError
from infoblox import infoblox
from . import testcasefixture


class TestCreateFixedAddress(testcasefixture.TestCaseWithFixture):
    fixture_name = 'fixedaddress_create'

    @classmethod
    def setUpClass(cls):
        super(TestCreateFixedAddress, cls).setUpClass()
        cls.iba_ipa = infoblox.Infoblox('10.10.10.10', 'foo', 'bar',
                                        '1.6', 'default', 'default')
        cls.post_url = 'https://10.10.10.10/wapi/v1.6/fixedaddress'

    @responses.activate
    def test_cname_create(self):
        responses.add(responses.POST, self.post_url, body=self.body, status=201)
        self.ret_val = self.iba_ipa.create_fixed_address('192.168.10.1',
                                                         'aa:bb:cc:dd:ee:ff')
        self.assertIsNotNone(self.ret_val)

    @responses.activate
    def test_cname_create_bad_reponse(self):
        responses.add(responses.POST, self.post_url, body=self.body, status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.create_fixed_address('192.168.10.1',
                                              'aa:bb:cc:dd:ee:ff')
