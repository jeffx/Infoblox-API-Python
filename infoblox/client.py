"""client.py - contains the Session, Infoblox, and Exception classes."""
import re

import requests
from six.moves import urllib


STATIC_FORMAT = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'
CIDR_FORMAT = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$'
RANGE_FORMAT = ('^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'
                '-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')


class InfobloxException(Exception):
    """Base exception for all exceptions raised."""

    pass


class ApiError(InfobloxException):
    """General purpose Infoblox API error."""

    def __init__(self, Error, code, text, trace=None):
        """Create an instance of an ApiError.

        :param str Error: error type (followed by an explanation after ":")
        :param str code: symbolic error code
        :param str text: explanation of the error
        :param str trace: debug trace from the server if debug is enabled
        """
        self.error = Error
        self.code = code
        self.text = text
        self.trace = trace
        super(ApiError, self).__init__(text)


class BadAddressError(ValueError, InfobloxException):
    """Error to indicate a bad address has been given."""

    def __init__(self, address):
        """Create an instance of a BadAddressError.

        :param address: the bad address
        """
        self.address = address
        msg = ('The given address ({!r}) was not one of the following address '
               'types: CIDR, IP range, or static IP.')
        super(BadAddressError, self).__init__(msg.format(address), address)


# TODO: should this not be an ApiError?
class TooManyResultsError(InfobloxException):
    """Error to indicate too many results were returned by the API."""

    def __init__(self, max_results):
        """Create an instance of a TooManyResultsError.

        :param int max_results: the max_results setting at the time the
                                exception was raised
        """
        msg = ('More results were returned than the max_results (={0}) '
               'setting allows. Please adjust your paging settings.')
        super(TooManyResultsError, self).__init__(msg.format(max_results),
                                                  max_results)
        self.max_results = max_results


def parse_address(address):
    """Parse the given address into the correct format for a query.

    :param str address: an internet address in one of the following formats:
                        CIDR, IP range, or static IP address
    :return: properly decorated address ready for use in a query
    :rtype: str
    """
    if re.match(CIDR_FORMAT, address) or re.match(RANGE_FORMAT, address):
        return 'func:nextavailableip:{0}'.format(address)
    if re.match(STATIC_FORMAT, address):
        return address
    raise BadAddressError('Expected address to be in CIDR format, an '
                          'address range, or a static IP address.')


class Session(requests.Session):
    """Custom requests session for use with the Infoblox API."""

    # TODO: look up when to specify the API version
    def __init__(self, url, version, auto_paging=True):
        """Create a new Infoblox Session instance.

        :param str url: base URL for an Infoblox server
        :param str version: API version to use
        :param bool auto_paging: true if additional result pages should be
                                 automatically requested; false otherwise
        """
        super(Session, self).__init__()
        self.endpoint = url, version
        self.auto_paging = auto_paging

    @property
    def endpoint(self):
        """Return the session's endpoint URL.

        :return: complete base URL
        :rtype: str
        """
        return self._endpoint

    @endpoint.setter
    def endpoint(self, value):
        """Set the sessions's endpoint URL by base URL and API version.

        :param tuple value: 2-tuple of base URL and API version
        """
        url, version = value
        path = 'wapi/v{0}/'.format(version)
        self._endpoint = urllib.parse.urljoin(url, path)

    # This is necessary because some of the URL paths contain colons, which
    # urllib naively interprets as a division between scheme and netloc.
    def _urlize(self, path):
        PATH = 2
        components = list(urllib.parse.urlsplit(self.endpoint))
        # Either the path is relative or absolute
        if path.startswith('/'):
            new_path = path
        else:
            old_path = components[PATH].rstrip('/')  # no double slashes
            new_path = '/'.join([old_path, path])
        components[PATH] = new_path
        return urllib.parse.urlunsplit(components)

    # This logic handles the use of the correct param for return fields while
    # also CSV'ing the given fields.
    def _get_fields(self, fields, fields_only):
        param = {}
        if fields is not None:
            if fields_only:
                field = '_return_fields'
            else:
                field = '_return_fields+'
            param = {field: ','.join(fields)}
        return param

    # Combine requests' raise_for_status and json methods for expediency.
    def _raise_for_status_or_get_json(self, response):
        try:
            response.raise_for_status()
        except Exception:
            raise ApiError(**response.json())
        return response.json()

    def get(self, resource, max_results=None, paging=False, page_id=None,
            return_fields=None, return_fields_only=False, **kwargs):
        """Get a resource.

        This implements the specifics of an Infoblox GET request.

        :param str resource: the relative path for a resource
        :param int max_results: the maximum results returned in each request
        :param bool paging: whether to request result paging
        :param int page_id: initial page of results to request
        :param list return_fields: the fields to return
        :param bool return_fields_only: whether to limit the fields returned
                                        to only those given
        """
        params = kwargs.pop('params', {})
        params['_max_results'] = max_results
        params['_paging'] = 1 if paging else 0
        params['_page_id'] = page_id
        params['_return_as_object'] = 1
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        url = self._urlize(resource)
        response = super(Session, self).get(url, params=params, **kwargs)
        data = self._raise_for_status_or_get_json(response)

        results = data['result']
        # next_page_id is only present if there are additional pages
        while 'next_page_id' in data and self.auto_paging:
            params['page_id'] = data['next_page_id']
            response = super(Session, self).get(url, params=params, **kwargs)
            data = self._raise_for_status_or_get_json(response)
            results.extend(data['result'])
        return results

    def post(self, resource, return_fields=None, return_fields_only=False, **kwargs):
        params = kwargs.pop('params', {})
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        url = self._urlize(resource)
        response = super(Session, self).post(url, params=params, **kwargs)
        return self._raise_for_status_or_get_json(response)

    def put(self, resource, return_fields=None, return_fields_only=False, **kwargs):
        params = kwargs.pop('params', {})
        fields = self._get_fields(return_fields, return_fields_only)
        params.update(fields)

        url = self._urlize(resource)
        response = super(Session, self).put(url, params=params, **kwargs)
        return self._raise_for_status_or_get_json(response)

    def delete(self, resource, **kwargs):
        url = self._urlize(resource)
        response = super(Session, self).delete(url, **kwargs)
        return self._raise_for_status_or_get_json(response)


class Infoblox(object):
    def __init__(self, url, username, password, version,
                 dns_view='default', network_view='default'):
        self.session = Session(url, version)
        self.session.auth = username, password
        self.session.verify = False
        self.views = {
            'dns': dns_view,
            'network': network_view,
        }

    ## API Functions

    def get_next_available_ips(self, network, count=1):
        network = self.get_network(network)
        params = {
            '_function': 'next_available_ip',
            'num': count,
        }
        data = self.session.post(network['_ref'], params=params)
        return data.get('ips', [])

    ## Host record

    def create_host_record(self, address, fqdn, is_dhcp=False):
        payload = {
            'name': fqdn,
            'view': self.views['dns'],
            'ipv4address': [{
                'ipv4addr': parse_address(address),
                'configure_for_dhcp': is_dhcp,
            }],
        }
        record = self.session.post('record:host', return_fields=['ipv4addrs'],
                                   json=payload)
        return record

    def get_host_records(self, fields=None):
        records = self.session.get('record:host', return_fields=fields)
        return records

    def get_host_record(self, fqdn, fields=None):
        params = {
            'name': fqdn,
            'view': self.views['dns'],
        }
        record = self.session.get('record:host', params=params,
                                  return_fields=fields)
        return record

    def delete_host_record(self, fqdn):
        record = self.get_host_record(fqdn)
        deleted_record = self.session.delete(record['_ref'])
        return deleted_record

    ## Txt record

    def create_txt_record(self, text, fqdn):
        payload = {
            'text': text,
            'name': fqdn,
            'view': self.views['dns'],
        }
        record = self.session.post('record:txt', json=payload)
        return record

    def get_txt_record(self, fqdn, fields=None):
        params = {
            'name': fqdn,
            'view': self.views['dns'],
        }
        record = self.session.get('record:txt', params=params,
                                  return_fields=fields)
        return record

    def delete_txt_record(self, fqdn):
        record = self.get_txt_record(fqdn)
        deleted_record = self.session.delete(record['_ref'])
        return deleted_record

    ## Host alias

    def create_host_alias(self, fqdn, alias):
        record = self.get_host_record(fqdn, fields=('name', 'aliases'))
        aliases = record.get('aliases', [])
        aliases.append(alias)
        payload = {'aliases': aliases}
        return self.session.put(record['_ref'], json=payload)

    def delete_host_alias(self, fqdn, alias):
        record = self.get_host_record(fqdn, fields=('name', 'aliases'))
        aliases = record.get('aliases', [])
        aliases.remove(alias)
        payload = {'aliases': aliases}
        return self.session.put(record['_ref'], json=payload)

    ## CNAME

    def create_cname_record(self, canonical, name):
        payload = {
            'canonical': canonical,
            'name': name,
            'view': self.views['dns'],
        }
        record = self.session.post('record:cname', json=payload)
        return record

    def get_cname_record(self, name):
        payload = {'name': name}
        record = self.session.get('record:cname', json=payload)
        return record

    def update_cname_record(self, canonical, name):
        record = self.get_cname_record(name)
        payload = {'canonical': canonical}
        updated_record = self.session.put(record['_ref'], json=payload)
        return updated_record

    def delete_cname_record(self, name):
        record = self.get_cname_record(name)
        deleted_record = self.session.delete(record['_ref'])
        return deleted_record

    ## DHCP range

    def create_dhcp_range(self, start, end):
        payload = {
            'start_addr': start,
            'end_addr': end,
        }
        dhcp_range = self.session.post('range', json=payload)
        return dhcp_range

    def get_dhcp_range(self, start, end):
        params = {
            'start_addr': start,
            'end_addr': end,
            'network_view': self.views['network'],
        }
        dhcp_range = self.session.get('range', params=params)
        return dhcp_range

    def delete_dhcp_range(self, start, end):
        dhcp_range = self.get_dhcp_range(start, end)
        deleted_dhcp_range = self.session.delete(dhcp_range['_ref'])
        return deleted_dhcp_range

    ## Network

    def create_network(self, network):
        payload = {
            'network': network,
            'network_view': self.views['network'],
        }
        network = self.session.post('network', json=payload)
        return network

    def get_networks(self, fields=None):
        networks = self.session.get('network', return_fields=fields)
        return networks

    def get_network(self, network, fields=None):
        params = {
            'network': network,
            'network_view': self.views['network'],
            '_return_fields': fields,
        }
        network = self.session.get('network', params=params,
                                   return_fields=fields)
        return network

    def get_network_extattrs(self, network):
        network = self.get_network(network, fields=('network', 'extattrs'))
        return {k: v['value'] for k, v in network['extattrs'].items()}

    def get_next_available_networks(self, container, cidr, count=1):
        container = self.get_network_container(container)
        params = {
            '_function': 'next_available_network',
            'cidr': cidr,
            'count': count,
        }
        data = self.session.post(container['_ref'], params=params)
        return data.get('networks', [])

    def delete_network(self, network):
        network = self.get_network(network)
        deleted_network = self.session.delete(network['_ref'])
        return deleted_network

    ## Network containers

    def create_network_container(self, container):
        payload = {
            'network': container,
            'network_view': self.views['network'],
        }
        container = self.session.post('networkcontainer', json=payload)
        return container

    def get_network_container(self, container):
        params = {
            'network': container,
            'network_view': self.views['network']
        }
        container = self.session.get('networkcontainer', params=params)
        return container

    def delete_network_container(self, container):
        container = self.get_network_container(container)
        deleted_container = self.session.delete(container['_ref'])
        return deleted_container

    ## A records

    def get_a_records(self, fields=None):
        records = self.session.get('record:a', return_fields=fields)
        return records

    def get_a_record_by_field(self, field, value, fields=None):
        params = {field: value}
        a_record = self.session.get('record:a', params=params,
                                    return_fields=fields)
        return a_record

    def get_a_record_by_ip(self, ip, **kwargs):
        return self.get_a_record_by_field(field='ipv4addr', value=ip, **kwargs)

    def get_a_record_by_fqdn(self, fqdn, **kwargs):
        return self.get_a_record_by_field(field='name', value=fqdn, **kwargs)

    ## Search utils

    def search_host_records(self, fqdn):
        params = {
            'name~': fqdn,
            'view': self.views['dns'],
        }
        records = self.session.get('record:host', params=params)
        return records

    def search_txt_records(self, fqdn):
        params = {
            'name~': fqdn,
            'view': self.views['dns'],
        }
        records = self.session.get('record:txt', params=params)
        return records

    ## Specific gets

    def get_address_by_ip(self, ip):
        params = {
            'ip_address': ip,
            'network_view': self.views['network'],
        }
        address = self.session.get('ipv4address', params=params)
        return address

    def get_host_ips(self, fqdn):
        record = self.get_host_record(fqdn)
        return (e['ipv4addr'] for e in record['ipv4addrs'])

    def get_host_extattrs(self, fqdn):
        record = self.get_host_record(fqdn)
        return {k: v['value'] for k, v in record['extattrs'].items()}

    def get_network_by_ip(self, ip):
        params = {
            'ip_address': ip,
            'network_view': self.views['network'],
        }
        network = self.session.get('ipv4address', params=params)
        return network

    def get_networks_by_extatts(self, attributes):
        params = {'*{}'.format(k): v for k, v in attributes.items()}
        params['network_view'] = self.views['network']
        networks = self.session.get('network', params=params)
        return (n for n in networks if 'network' in n)

    def get_host_by_extattrs(self, attributes):
        params = {'*{}'.format(k): v for k, v in attributes.items()}
        params['view'] = self.views['dns']
        record = self.session.get('record:host', params=params)
        return (r for r in record if 'name' in r)
