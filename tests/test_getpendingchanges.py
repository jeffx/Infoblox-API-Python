import responses
from requests.exceptions import HTTPError
from . import testcasefixture


class TestGetPendingChanges(testcasefixture.TestCaseWithFixture):
    fixture_name = 'pendingchanges_get'

    @classmethod
    def setUpClass(cls):
        super(TestGetPendingChanges, cls).setUpClass()
        cls.base_url = 'https://10.10.10.10/wapi/v1.6/'
        cls.get_url = '%sgrid:servicerestart:request:changedobject' % (cls.base_url)
        cls.ip = '192.168.1.10'

    @responses.activate
    def test_get_pending_changes_returns_object_name(self):
        responses.add(responses.GET, self.get_url, body=self.body, status=200)
        self.r_json = self.iba_ipa.get_pending_changes()
        self.assertEqual(self.ip, self.r_json[0]['object_name'])

    @responses.activate
    def test_get_pending_changes_badresponse(self):
        responses.add(responses.GET, self.get_url, body='[]', status=500)
        with self.assertRaises(HTTPError):
            self.iba_ipa.get_pending_changes()
