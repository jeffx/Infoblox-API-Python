#
# Copyright 2014 "Igor Feoktistov" <ifeoktistov@yahoo.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
import requests
import json
from six.moves import urllib


class InfobloxException(Exception):
    pass


class InfobloxNotFoundException(InfobloxException):
    pass


class InfobloxNotUpdatedException(InfobloxException):
    pass


class InfobloxNoIPavailableException(InfobloxException):
    pass


class InfobloxNoNetworkAvailableException(InfobloxException):
    pass


class InfobloxGeneralException(InfobloxException):
    pass


class InfobloxBadInputParameter(InfobloxException):
    pass


class Infoblox(object):
    """A client for the Infoblox IPAM API.

    Implements the following subset of Infoblox IPAM API via REST API:

        - create_network
        - delete_network
        - create_networkcontainer
        - delete_networkcontainer
        - get_next_available_network
        - create_host_record
        - create_txt_record
        - delete_txt_record
        - delete_host_record
        - add_host_alias
        - delete_host_alias
        - get_a_record_by_ip
        - get_a_record_by_fqdn
        - get_cname_record
        - create_cname_record
        - delete_cname_record
        - update_cname_record
        - create_dhcp_range
        - delete_dhcp_range
        - get_next_available_ip
        - get_host
        - get_host_by_ip
        - get_ip_by_host
        - get_host_by_regexp
        - get_txt_by_regexp
        - get_host_by_extattrs
        - get_host_extattrs
        - get_network
        - get_network_by_ip
        - get_network_by_extattrs
        - get_network_extattrs
        - update_network_extattrs
        - delete_network_extattrs
    """

    def __init__(self, iba_ipaddr, iba_user, iba_password, iba_wapi_version,
                 iba_dns_view, iba_network_view, iba_verify_ssl=False):
        """Create a client for a particular infoblox server.

        :param str iba_ipaddr: IBA IP address of management interface
        :param str iba_user: IBA user name
        :param striba_password: IBA user password
        :param str iba_wapi_version: IBA WAPI version (example: 1.0)
        :param str iba_dns_view: IBA default view
        :param str iba_network_view: IBA default network view
        :param str iba_verify_ssl: IBA SSL certificate validation (example: False)
        """
        self.iba_host = iba_ipaddr
        self.iba_user = iba_user
        self.iba_password = iba_password
        self.iba_wapi_version = iba_wapi_version
        self.iba_dns_view = iba_dns_view
        self.iba_network_view = iba_network_view
        self.iba_verify_ssl = iba_verify_ssl
        self.base_url = 'https://{0.iba_host}/wapi/v/{0.iba_wapi_version}/'
        self._setup_session()

        self.util = Util(self.session,
                         iba_ipaddr, iba_user, iba_password,
                         iba_wapi_version, iba_dns_view, iba_network_view,
                         iba_verify_ssl)

    def make_url(self, path):
        """Return a complete URL given just the path.

        :param str path: relative path for the URL
        :return: an absolute URL
        :rtype: str
        """
        base = self.base_url.format(self)
        return urllib.parse.urljoin(base, path)

    def _setup_session(self):
        self.session = requests.Session()
        self.session.auth = (self.iba_user, self.iba_password)
        self.session.verify = self.iba_verify_ssl

    def get_next_available_ip(self, network):
        """Return the next available IP address given a network.

        :param str network: network in CIDR format
        :return: IPv4 address
        :rtype: str
        """
        params = {
            'network': network,
            'netowrk_view': self.iba_network_view,
        }
        rest_url = self.make_url(path='network')
        try:
            r = self.session.get(url=rest_url, params=params)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    net_ref = r_json[0]['_ref']
                    rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                        self.iba_wapi_version + '/' + net_ref + \
                        '?_function=next_available_ip&num=1'
                    r = self.session.post(url=rest_url)
                    r_json = r.json()
                    if r.status_code == 200:
                        ip_v4 = r_json['ips'][0]
                        return ip_v4
                    else:
                        if 'text' in r_json:
                            if ('code' in r_json and
                                    r_json['code'] == 'Client.Ibap.Data'):
                                raise InfobloxNoIPavailableException(
                                    r_json['text'])
                            else:
                                raise InfobloxGeneralException(r_json['text'])
                        else:
                            r.raise_for_status()
                else:
                    raise InfobloxNotFoundException(
                        "No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_host_record(self, address, fqdn, payload=None):
        """Create a host record given an address and an FQDN.

        Returns IP v4 address assigned to the host
        :param str address: IP v4 address or NET v4 address in CIDR format
        :param str fqdn: hostname in FQDN
        :return: IP addresss given to the host
        :rtype: str
        """
        cidr_address = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$'
        address_range = ('^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'
                         '-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
        static_address = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'

        if re.match(cidr_address, address):
            ipv4addr = 'func:nextavailableip:' + address
        elif re.match(address_range, address):
            ipv4addr = 'func:nextavailableip:' + address
        elif re.match(static_address, address):
            ipv4addr = address
        else:
            raise InfobloxBadInputParameter('Expected IP or NET address in '
                                            'CIDR format, an address range, '
                                            'or a static address.')

        if payload is None:
            payload = {
                'name': fqdn,
                'view': self.iba_dns_view,
                'ipv4addrs': [
                    {
                        'ipv4addr': ipv4addr,
                        'configure_for_dhcp': False,
                    }
                ]
            }

        r_json = self.util.post('record:host', payload=payload,
                                fields=['ipv4addrs'])
        if r_json is None:
            raise InfobloxGeneralException('Failed to create host record '
                                           'for [{}]'.format(address))
        return r_json['ipv4addrs'][0]['ipv4addr']

    def get_cname_record(self, fqdn):
        """Return the CNAME record given an FQDN.

        :param str fqdn: hostname in FQDN
        :return: CNAME record
        :rtype: dict
        """
        # canonical instead of name?
        rest_url = "{}/record:cname?name={}".format(self.base_url, fqdn)
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    cname_ref = r_json[0]['_ref']
                    if cname_ref and re.match("record:cname\/[^:]+:([^\/]+)\/", cname_ref).group(1) == fqdn:
                        return r_json[0]
                    else:
                        msg = 'Received unexpected cname record reference: {}'
                        raise InfobloxGeneralException(msg.format(cname_ref))
                else:
                    msg = 'No requested cname record found: {}'
                    raise InfobloxNotFoundException(msg.format(fqdn))
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_txt_record(self, text, fqdn):
        """Create a txt record given the text and an FQDN.

        :param str text: free text to be added to the record
        :param str fqdn: hostname in FQDN
        """
        rest_url = 'https://{0.iba_host}/wapi/v/{0.iba_wapi_version}/record:txt'
        rest_url = rest_url.format(self)

        payload = {
            'text': text,
            'name': fqdn,
            'view': self.iba_dns_view,
        }
        try:
            r = self.session.post(url=rest_url, json=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return
            if 'text' in r_json:
                raise InfobloxGeneralException(r_json['text'])
            else:
                r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_host_record(self, fqdn):
        """Delete a host record given an FQDN.

        :param str fqdn: FQDN of the host record
        """
        rest_url = ('https://{0.iba_host}/wapi/v/{0.iba_wapi_version}'
                    '/record:host?name={1}&view={0.iba_dns_view}')
        rest_url = rest_url.format(self, fqdn)
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if (host_ref and
                            re.match("record:host\/[^:]+:([^\/]+)\/",
                                     host_ref).group(1) == fqdn):
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + host_ref
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested host found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_txt_record(self, fqdn):
        """ Implements IBA REST API call to delete IBA TXT record
        :param fqdn: hostname in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:txt?name=' + fqdn + \
            '&view=' + self.iba_dns_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if (host_ref and
                        re.match("record:txt\/[^:]+:([^\/]+)\/",
                                 host_ref).group(1) == fqdn):
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + host_ref
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested host found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def add_host_alias(self, host_fqdn, alias_fqdn):
        """ Implements IBA REST API call to add an alias to IBA host record
        :param host_fqdn: host record name in FQDN
        :param alias_fqdn: host record name in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?name=' + host_fqdn + \
            '&view=' + self.iba_dns_view + '&_return_fields=name,aliases'
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if (host_ref and
                        re.match("record:host\/[^:]+:([^\/]+)\/",
                                 host_ref).group(1) == host_fqdn):
                        if 'aliases' in r_json[0]:
                            aliases = r_json[0]['aliases']
                            aliases.append(alias_fqdn)
                            payload = '{"aliases": ' + \
                                json.JSONEncoder().encode(aliases) + '}'
                        else:
                            payload = '{"aliases": ["' + alias_fqdn + '"]}'
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + host_ref
                        r = self.session.put(url=rest_url, data=payload)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested host found: " + host_fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_host_alias(self, host_fqdn, alias_fqdn):
        """ Implements IBA REST API call to add an alias to IBA host record
        :param host_fqdn: host record name in FQDN
        :param alias_fqdn: host record name in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?name=' + host_fqdn + \
            '&view=' + self.iba_dns_view + '&_return_fields=name,aliases'
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    host_ref = r_json[0]['_ref']
                    if (host_ref
                            and re.match("record:host\/[^:]+:([^\/]+)\/",
                                         host_ref).group(1) == host_fqdn):
                        if 'aliases' in r_json[0]:
                            aliases = r_json[0]['aliases']
                            aliases.remove(alias_fqdn)
                            payload = '{"aliases": ' \
                                + json.JSONEncoder().encode(aliases) + '}'
                            rest_url = 'https://' + self.iba_host + \
                                '/wapi/v' + self.iba_wapi_version + \
                                '/' + host_ref
                            r = self.session.put(url=rest_url, data=payload)
                            if r.status_code == 200:
                                return
                            else:
                                if 'text' in r_json:
                                    raise InfobloxGeneralException(
                                        r_json['text'])
                                else:
                                    r.raise_for_status()
                        else:
                            raise InfobloxNotFoundException(
                                "No requested host alias found: " + alias_fqdn)
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected host reference: " + host_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested host found: " + host_fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_cname_record(self, canonical, name):
        """ Implements IBA REST API call to create IBA cname record
        :param canonical: canonical name in FQDN format
        :param name: the name for a CNAME record in FQDN format
        """
        rest_url = "{0}/record:cname".format(self.base_url)
        payload = {"canonical": canonical,
                   "name": name,
                   "view": self.iba_dns_view}
        try:
            r = self.session.post(url=rest_url, data=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_cname_record(self, fqdn):
        """ Implements IBA REST API call to delete IBA cname record
        :param fqdn: cname in FQDN
        """
        rest_url = "{0}/record:cname?name={1}&view={2}".format(
            self.base_url, fqdn, self.iba_dns_view)
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    cname_ref = r_json[0]['_ref']
                    if (cname_ref and
                            re.match("record:cname\/[^:]+:([^\/]+)\/",
                                     cname_ref).group(1) == fqdn):
                        rest_url = "{0}/{1}".format(self.base_url, cname_ref)
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected cname record  reference: " + cname_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested cname record found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def update_cname_record(self, canonical, name):
        """ Implements IBA REST API call to update or repoint IBA cname record
        :param canonical: canonical name in FQDN format
        :param name: the name for the new CNAME record in FQDN format
        """
        rest_url = 'https://' + self.iba_host + \
            '/wapi/v' + self.iba_wapi_version + '/record:cname'
        payload = json.dumps({'name': name})
        try:
            r = self.session.get(url=rest_url, data=payload)
            r_json = r.json()
            # RFC1912 - A CNAME can not coexist with any other data, we
            # should expect utmost one entry
            if r.status_code == 200 and len(r_json) == 1:
                ibx_cname = r.json()[0]
                cname_ref = ibx_cname['_ref']
                payload = '{"canonical": ' + \
                    json.JSONEncoder().encode(canonical) + '}'
                rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                    self.iba_wapi_version + '/' + cname_ref
                r = self.session.put(url=rest_url, data=payload)
                if r.status_code == 200 or r.status_code == 201:
                    return
                else:
                    r.raise_for_status()
            elif len(r_json) == 0:
                raise InfobloxNotFoundException("CNAME: " +
                                                name + " not found.")
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_dhcp_range(self, start_ip_v4, end_ip_v4):
        """ Implements IBA REST API call to add DHCP range for given
            start and end addresses
        :param start_ip_v4: IP v4 address
        :param end_ip_v4: IP v4 address
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/range'
        payload = '{"start_addr": "' + start_ip_v4 + \
            '","end_addr": "' + end_ip_v4 + '"}'
        try:
            r = self.session.post(url=rest_url, data=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_dhcp_range(self, start_ip_v4, end_ip_v4):
        """ Implements IBA REST API call to delete DHCP range for given
            start and end addresses
        :param start_ip_v4: IP v4 address
        :param end_ip_v4: IP v4 address
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/range?start_addr=' + \
            start_ip_v4 + '?end_addr=' + end_ip_v4 + '&network_view=' + \
            self.iba_network_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    range_ref = r_json[0]['_ref']
                    if range_ref:
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + range_ref
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "No range reference received in IBA reply")
                else:
                    raise InfobloxNotFoundException(
                        "No requested range found: " + start_ip_v4 + "-" + end_ip_v4)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_host(self, fqdn, fields=None, notFoundFail=True):
        """ Implements IBA REST API call to retrieve host record fields
        Returns hash table of fields with field name as a hash key
        :param fqdn: hostname in FQDN
        :param fields: comma-separated list of field names (optional)
        """
        r_json = self.util.get('record:host',
                               query_params={
                                   'name': fqdn,
                                   'view': self.iba_dns_view
                               },
                               fields=fields,
                               notFoundText="No hosts found: " + fqdn,
                               notFoundFail=notFoundFail
                               )
        if r_json is None and notFoundFail is False:
            return r_json
        return r_json[0]

    def get_host_by_regexp(self, fqdn):
        """ Implements IBA REST API call to retrieve host records by fqdn regexp filter
        Returns array of host names in FQDN matched to given regexp filter
        :param fqdn: hostname in FQDN or FQDN regexp filter
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?name~=' + \
            fqdn + '&view=' + self.iba_dns_view
        hosts = []
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    for host in r_json:
                        hosts.append(host['name'])
                    return hosts
                else:
                    raise InfobloxNotFoundException(
                        "No hosts found for regexp filter: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_txt_by_regexp(self, fqdn):
        """ Implements IBA REST API call to retrieve TXT records by fqdn
            regexp filter
        Returns dictonary of host names in FQDN matched to given regexp
            filter with the TXT value
        :param fqdn: hostname in FQDN or FQDN regexp filter
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:txt?name~=' + fqdn + \
            '&view=' + self.iba_dns_view
        hosts = {}
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    for host in r_json:
                        hosts[host['name']] = host['text']
                    return hosts
                else:
                    raise InfobloxNotFoundException(
                        "No txt records found for regexp filter: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_host_by_ip(self, ip_v4, fields=None, notFoundFail=True):
        """ Implements IBA REST API call to find hostname by IP address
        Returns array of host names in FQDN associated with given IP address
        :param ip_v4: IP v4 address
        """
        r_json = self.get_ipv4address_by_ip(ip_v4, fields, notFoundFail)
        if r_json is None and notFoundFail is False:
            return r_json
        return r_json['names']

    def get_ipv4address_by_ip(self, ip_v4, fields=None, notFoundFail=True):
        """ Implements IBA REST API call to find hostname by IP address
        Returns ipv4address details associated with given IP address
        :param ip_v4: IP v4 address
        """
        r_json = self.util.get('ipv4address',
                               query_params={
                                   'ip_address': ip_v4,
                                   'network_view': self.iba_network_view
                               },
                               fields=fields,
                               notFoundText="No IP found: " + ip_v4,
                               notFoundFail=notFoundFail
                               )
        if r_json is None and notFoundFail is False:
            return r_json
        return r_json[0]

    def get_ip_by_host(self, fqdn):
        """ Implements IBA REST API call to find IP addresses by hostname
        Returns array of IP v4 addresses associated with given hostname
        :param fqdn: hostname in FQDN
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?name=' + \
            fqdn + '&view=' + self.iba_dns_view
        ipv4addrs = []
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    if len(r_json[0]['ipv4addrs']) > 0:
                        for ipv4addr in r_json[0]['ipv4addrs']:
                            ipv4addrs.append(ipv4addr['ipv4addr'])
                        return ipv4addrs
                    else:
                        raise InfobloxNotFoundException(
                            "No host records found for FQDN: " + fqdn)
                else:
                    raise InfobloxNotFoundException("No hosts found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_host_extattrs(self, fqdn, attributes=None):
        """ Implements IBA REST API call to retrieve host extensible attributes
        Returns hash table of attributes with attribute name as a hash key
        :param fqdn: hostname in FQDN
        :param attributes: array of extensible attribute names (optional)
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?name=' + fqdn + \
            '&view=' + self.iba_dns_view + '&_return_fields=name,extattrs'
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    extattrs = {}
                    if attributes:
                        for attribute in attributes:
                            if attribute in r_json[0]['extattrs']:
                                extattrs[attribute] = \
                                    r_json[0]['extattrs'][attribute]['value']
                            else:
                                raise InfobloxNotFoundException(
                                    "No requested attribute found: " + attribute)
                    else:
                        for attribute in r_json[0]['extattrs'].keys():
                            extattrs[attribute] = \
                                r_json[0]['extattrs'][attribute]['value']
                    return extattrs
                else:
                    raise InfobloxNotFoundException(
                        "No requested host found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_network(self, network, fields=None):
        """ Implements IBA REST API call to retrieve network object fields
        Returns hash table of fields with field name as a hash key
        :param network: network in CIDR format
        :param fields: comma-separated list of field names
            (optional, returns network in CIDR format and netmask if
             not specified)
        """
        if not fields:
            fields = 'network,netmask'
        if type(fields) is not str:
            fields = ','.join(fields)
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?network=' + network + \
            '&network_view=' + self.iba_network_view + '&_return_fields=' + \
            fields
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    return r_json[0]
                else:
                    raise InfobloxNotFoundException(
                        "No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_network_by_ip(self, ip_v4):
        """ Implements IBA REST API call to find network by IP address which
            belongs to this network
        Returns network in CIDR format
        :param ip_v4: IP v4 address
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/ipv4address?ip_address=' + ip_v4 + \
            '&network_view=' + self.iba_network_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    if 'network' in r_json[0]:
                        return r_json[0]['network']
                    else:
                        raise InfobloxNotFoundException(
                            "No network found for IP: " + ip_v4)
                else:
                    raise InfobloxNotFoundException("No IP found: " + ip_v4)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_network_by_extattrs(self, attributes):
        """ Implements IBA REST API call to find a network by it's
            extensible attributes
        Returns array of networks in CIDR format
        :param attributes: comma-separated list of attrubutes name/value
            pairs in the format:
            attr_name=attr_value - exact match for attribute value
            attr_name:=attr_value - case insensitive match for attribute value
            attr_name~=regular_expression - match attribute value by regular
                expression
            attr_name>=attr_value - search by number greater than value
            attr_name<=attr_value - search by number less than value
            attr_name!=attr_value - search by number not equal of value
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?*' + \
            "&*".join(attributes.split(",")) + '&network_view=' + \
            self.iba_network_view
        networks = []
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    for network in r_json:
                        if 'network' in network:
                            networks.append(network['network'])
                    return networks
                else:
                    raise InfobloxNotFoundException(
                        "No networks found for extensible attributes: " + attributes)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_host_by_extattrs(self, attributes):
        """ Implements IBA REST API call to find host by it's extensible attributes
        Returns array of hosts in FQDN
        :param attributes: comma-separated list of attrubutes name/value
            pairs in the format:
            attr_name=attr_value - exact match for attribute value
            attr_name:=attr_value - case insensitive match for attribute value
            attr_name~=regular_expression - match attribute value by regular
                expression
            attr_name>=attr_value - search by number greater than value
            attr_name<=attr_value - search by number less than value
            attr_name!=attr_value - search by number not equal of value
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/record:host?*' + \
            "&*".join(attributes.split(",")) + '&view=' + self.iba_dns_view
        hosts = []
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    for host in r_json:
                        if 'name' in host:
                            hosts.append(host['name'])
                    return hosts
                else:
                    raise InfobloxNotFoundException(
                        "No hosts found for extensible attributes: " + attributes)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_network_extattrs(self, network, attributes=None):
        """ Implements IBA REST API call to retrieve network extensible attributes
        Returns hash table of attributes with attribute name as a hash key
        :param network: network in CIDR format
        :param attributes: array of extensible attribute names (optional)
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?network=' + network + \
            '&network_view=' + self.iba_network_view + \
            '&_return_fields=network,extattrs'
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    extattrs = {}
                    if attributes:
                        for attribute in attributes:
                            if attribute in r_json[0]['extattrs']:
                                extattrs[attribute] = \
                                    r_json[0]['extattrs'][attribute]['value']
                            else:
                                raise InfobloxNotFoundException(
                                    "No requested attribute found: " + attribute)
                    else:
                        for attribute in r_json[0]['extattrs'].keys():
                            extattrs[attribute] = \
                                r_json[0]['extattrs'][attribute]['value']
                        return extattrs
                else:
                    raise InfobloxNotFoundException(
                        "No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxNotFoundException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def update_network_extattrs(self, network, attributes):
        """ Implements IBA REST API call to add or update network extensible attributes
        :param network: network in CIDR format
        :param attributes: hash table of extensible attributes with attribute
            name as a hash key
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?network=' + \
            network + '&network_view=' + self.iba_network_view + \
            '&_return_fields=network,extattrs'
        extattrs = {}
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    network_ref = r_json[0]['_ref']
                    if network_ref:
                        extattrs = r_json[0]['extattrs']
                        for attr_name, attr_value in attributes.iteritems():
                            extattrs[attr_name]['value'] = attr_value
                        payload = '{"extattrs": ' + \
                            json.JSONEncoder().encode(extattrs) + '}'
                        rest_url = 'https://' + self.iba_host + \
                            '/wapi/v' + self.iba_wapi_version + \
                            '/' + network_ref
                        r = self.session.put(url=rest_url, data=payload)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "No network reference received in IBA reply for network: " + network)
                else:
                    raise InfobloxNotFoundException(
                        "No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_network_extattrs(self, network, attributes):
        """ Implements IBA REST API call to delete network extensible attributes
        :param network: network in CIDR format
        :param attributes: array of extensible attribute names
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?network=' + \
            network + '&network_view=' + self.iba_network_view + \
            '&_return_fields=network,extattrs'
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    network_ref = r_json[0]['_ref']
                    if network_ref:
                        extattrs = r_json[0]['extattrs']
                        for attribute in attributes:
                            if attribute in extattrs:
                                del extattrs[attribute]
                        payload = '{"extattrs": ' + \
                            json.JSONEncoder().encode(extattrs) + '}'
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + network_ref
                        r = self.session.put(url=rest_url, data=payload)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "No network reference received in IBA reply for network: " + network)
                else:
                    raise InfobloxNotFoundException(
                        "No requested network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_network(self, network):
        """ Implements IBA REST API call to create DHCP network object
        :param network: network in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network'
        payload = '{"network": "' + network + '","network_view": "' + \
            self.iba_network_view + '"}'
        try:
            r = self.session.post(url=rest_url, data=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_network(self, network):
        """ Implements IBA REST API call to delete DHCP network object
        :param network: network in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/network?network=' + \
            network + '&network_view=' + self.iba_network_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    network_ref = r_json[0]['_ref']
                    if network_ref:
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + network_ref
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "No network reference received in IBA reply for network: " + network)
                else:
                    raise InfobloxNotFoundException(
                        "No network found: " + network)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def create_networkcontainer(self, networkcontainer):
        """ Implements IBA REST API call to create DHCP network containert object
        :param networkcontainer: network container in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/networkcontainer'
        payload = '{"network": "' + networkcontainer + \
            '","network_view": "' + self.iba_network_view + '"}'
        try:
            r = self.session.post(url=rest_url, data=payload)
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def delete_networkcontainer(self, networkcontainer):
        """ Implements IBA REST API call to delete DHCP network container object
        :param networkcontainer: network container in CIDR format
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/networkcontainer?network=' + \
            networkcontainer + '&network_view=' + self.iba_network_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    network_ref = r_json[0]['_ref']
                    if network_ref:
                        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                            self.iba_wapi_version + '/' + network_ref
                        r = self.session.delete(url=rest_url)
                        if r.status_code == 200:
                            return
                        else:
                            if 'text' in r_json:
                                raise InfobloxGeneralException(r_json['text'])
                            else:
                                r.raise_for_status()
                    else:
                        raise InfobloxGeneralException(
                            "No network container reference received in IBA reply for network container: " + networkcontainer)
                else:
                    raise InfobloxNotFoundException(
                        "No network container found: " + networkcontainer)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_next_available_network(self, networkcontainer, cidr):
        """ Implements IBA REST API call to retrieve next available network
            of network container
        Returns network address in CIDR format
        :param networkcontainer: network container address in CIDR format
        :param cidr: requested network length (from 0 to 32)
        """
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
            self.iba_wapi_version + '/networkcontainer?network=' + \
            networkcontainer + '&network_view=' + self.iba_network_view
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    net_ref = r_json[0]['_ref']
                    rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                        self.iba_wapi_version + '/' + net_ref + \
                        '?_function=next_available_network&cidr=' + \
                        str(cidr) + '&num=1'
                    r = self.session.post(url=rest_url)
                    r_json = r.json()
                    if r.status_code == 200:
                        network = r_json['networks'][0]
                        return network
                    else:
                        if 'text' in r_json:
                            if ('code' in r_json and
                                    r_json['code'] == 'Client.Ibap.Data'):
                                raise InfobloxNoNetworkAvailableException(
                                    r_json['text'])
                            else:
                                raise InfobloxGeneralException(r_json['text'])
                        else:
                            r.raise_for_status()
                else:
                    raise InfobloxNotFoundException(
                        "No requested network container found: " + networkcontainer)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def get_a_record_by_ip(self, ipaddr, fields=None, not_found_fail=True):
        """Retrieve A record by IP Address
        :param ipaddr: IP address for which we want information
        :param fields: comma-separated list of field names (optional)
        :param not_found_fail: Raise an exception if nothing is found.
        """

        r_json = self.util.get('record:a',
                               query_params={
                                   'ipv4addr': ipaddr
                               },
                               fields=fields,
                               notFoundText="No A record found: " + ipaddr,
                               notFoundFail=not_found_fail
                               )
        return r_json

    def get_a_record_by_fqdn(self, fqdn):
        """Retrieve A record by FQDN
        :param fqdn: FQDN for which we want information
        """

        # canonical instead of name?
        rest_url = "{}/record:a?name={}".format(self.base_url, fqdn)
        try:
            r = self.session.get(url=rest_url)
            r_json = r.json()
            if r.status_code == 200:
                if len(r_json) > 0:
                    a_ref = r_json[0]['_ref']
                    if a_ref and re.match("record:a\/[^:]+:([^\/]+)\/", a_ref).group(1) == fqdn:
                        return r_json[0]
                    else:
                        raise InfobloxGeneralException(
                            "Received unexpected A record  reference: " + a_ref)
                else:
                    raise InfobloxNotFoundException(
                        "No requested A record found: " + fqdn)
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def update_record(self, record, fields, confirm):
        self.util.put(record, fields, confirm)


class Util(object):

    def __init__(self,
                 session,
                 iba_ipaddr,
                 iba_user,
                 iba_password,
                 iba_wapi_version,
                 iba_dns_view,
                 iba_network_view,
                 iba_verify_ssl=False):
        """ Class initialization method
        :param session: Request session.
        :param iba_ipaddr: IBA IP address of management interface
        :param iba_user: IBA user name
        :param iba_password: IBA user password
        :param iba_wapi_version: IBA WAPI version (example: 1.0)
        :param iba_dns_view: IBA default view
        :param iba_network_view: IBA default network view
        :param iba_verify_ssl: IBA SSL certificate validation (example: False)
        """
        self.session = session
        self.iba_host = iba_ipaddr
        self.iba_user = iba_user
        self.iba_password = iba_password
        self.iba_wapi_version = iba_wapi_version
        self.iba_dns_view = iba_dns_view
        self.iba_network_view = iba_network_view
        self.iba_verify_ssl = iba_verify_ssl

    def get(self, uri, query_params=None, fields=None,
            notFoundText=None, notFoundFail=True):
        """Execute a get operation.
        :param uri: The URI component (e.g. -- lease, record:a)
        :param query_params: Key/Value query parameter dictonary.
        :param return_fields: String or list of fields to return.
        :param notFoundText: Exception text when get returns no data.
        :param notFoundFail: Raise an exception if nothing is found.
        """

        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                   self.iba_wapi_version + '/' + uri

        if query_params is None:
            query_params = {}
        if fields is not None:
            if type(fields) == str:
                query_params['_return_fields'] = fields
            else:
                query_params['_return_fields'] = ','.join(fields)

        try:
            if False:  # If debug is enabled, etc...
                print("util.get([%s][%s][%s][%s]" %
                      (uri, query_params, fields, notFoundText))
                print(rest_url + '?' +
                      '&'.join("%s=%s" % (key, val)
                               for (key, val) in query_params.items()))

            r = self.session.get(url=rest_url,
                                 params=query_params)

            r_json = r.json()

            if False:  # If debug is enabled, etc...
                print("RESULT")
                print(r)
                print(r_json)

            if r.status_code == 200:
                if len(r_json) > 0:
                    return r_json
                elif notFoundFail:
                    raise InfobloxNotFoundException(notFoundText)
                else:
                    return None
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)

    def put(self, record, payload, confirm=True):
        """Execute a put operation to update a record.
        :param record: The record to update.
        :param payload: payload to be updated.
        """

        ref = record['_ref']
        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                   self.iba_wapi_version + '/' + ref

        print("Update [%s] with [%s]" % (rest_url, payload))
        if not confirm:
            print("DRY-RUN -- NO CHANGES MADE")
            return

        r = self.session.put(url=rest_url,
                             data=json.dumps(payload))

        if r.status_code == 200:
            return

        raise InfobloxNotUpdatedException("Failed to update " + ref)

    def post(self, uri, payload, fields, confirm=True):

        rest_url = 'https://' + self.iba_host + '/wapi/v' + \
                   self.iba_wapi_version + '/' + uri

        print("Create [%s] with [%s] returning [%s]" %
              (rest_url, payload, fields))

        if not confirm:
            print("DRY-RUN -- NO CHANGES MADE")
            return

        query_params = {}
        if fields is not None:
            if type(fields) == str:
                query_params['_return_fields'] = fields
            else:
                query_params['_return_fields'] = ','.join(fields)

        try:
            r = self.session.post(url=rest_url,
                                  params=query_params,
                                  data=json.dumps(payload))
            r_json = r.json()
            if r.status_code == 200 or r.status_code == 201:
                return r_json
            else:
                if 'text' in r_json:
                    raise InfobloxGeneralException(r_json['text'])
                else:
                    r.raise_for_status()
        except ValueError:
            raise InfobloxGeneralException(r)
