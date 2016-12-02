"""client.py - contains the Infoblox client class."""
import re

from . import exceptions
from . import session


STATIC_FORMAT = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'
CIDR_FORMAT = '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\/[0-9]+$'
RANGE_FORMAT = ('^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'
                '-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')


# Parse the given address into the correct format for a query.
def _parse_ipv4addr(address):
    if re.match(CIDR_FORMAT, address) or re.match(RANGE_FORMAT, address):
        return 'func:nextavailableip:{0}'.format(address)
    if re.match(STATIC_FORMAT, address):
        return address
    raise exceptions.BadAddressError('Expected address to be in CIDR format, '
                                     'an address range, or a static IP '
                                     'address.')


class Infoblox(object):

    def __init__(self, url, username, password, version, dns_view='default',
                 network_view='default'):
        """Create a new Infoblox client.

        :param str url: scheme and domain of the API endpoint
        :param str username: username for API authentication
        :param str password: password for API authentication
        :param str version: x.y version of the API to use
        :param str dns_view: name of the DNS view to use
        :param str network_view: name of the network view to use
        """
        self.session = session.Session(url, version)
        self.session.auth = username, password
        self.session.verify = False
        self.views = {
            'dns': dns_view,
            'network': network_view,
        }

    # API Functions

    def get_next_available_ips(self, network, count=1):
        """Return the next *count* available IPs in a given *network*.

        :param str network: network to search
        :param int count: maximum number of available IPs to get
        :return: list of available IPs in the given network
        :rtype: list
        """
        network = self.get_network(network)
        params = {
            '_function': 'next_available_ip',
            'num': count,
        }
        data = self.session.post(network['_ref'], params=params)
        return data.get('ips', [])  # TODO: will none ever be returned?

    def get_next_available_networks(self, container, cidr, count=1):
        container = self.get_network_container(container)
        params = {
            '_function': 'next_available_network',
            'cidr': cidr,
            'count': count,
        }
        data = self.session.post(container['_ref'], params=params)
        return data.get('networks', [])  # TODO: will none ever be returned?

    # Host record

    def create_host_record(self, address, fqdn, is_dhcp=False):
        """Create a new host record for the given *address*.

        :param str address: the addres of the host
        :param str fqdn: the FQDN of the host
        :param bool is_dhcp: whether the host uses DHCP
        :return: the host record created
        :rtype: dict
        """
        payload = {
            'name': fqdn,
            'view': self.views['dns'],
            'ipv4address': [{
                'ipv4addr': _parse_ipv4addr(address),
                'configure_for_dhcp': is_dhcp,
            }],
        }
        record = self.session.post('record:host', return_fields=['ipv4addrs'],
                                   json=payload)
        return record

    def get_host_records(self, fields=None):
        """Return all host records.

        :param list fields: additional fields to return
        :return: all host records with the given fields
        :rtype: list
        """
        records = self.session.get('record:host', return_fields=fields)
        return records

    def get_host_record(self, fqdn, fields=None):
        """Get the host record with the given *fqdn*.

        :param str fqdn: the FQDN of the host record to return
        :param list fields: additional fields to return
        :return: a host record if one exists
        :rtype: dict
        :raises exceptions.NotFoundError: if the host record cannot be found
        """
        query = {'name': fqdn}
        records = self.search_host_records(query, fields=fields)
        try:
            return records[0]
        except IndexError:
            raise exceptions.NotFoundError('host record', fqdn)

    def get_host_record_by_mac(self, mac, fields=None):
        """Get the host record with the given *mac*.

        :param str mac: the MAC address
        :param list fields: additional fields to return
        :return: a host record
        :rtype: dict
        :raises exceptions.NotFoundError: if the host record cannot be found
        """
        query = {'mac:': mac}
        records = self.search_host_records(query, fields=fields)
        try:
            return records[0]
        except IndexError:
            raise exceptions.NotFoundError('host record', mac)

    def delete_host_record(self, fqdn):
        """Delete the host record with the given *fqdn*.

        :param str fqdn: the FQDN of the host record
        :return: object reference to the host record deleted
        :rtype: str
        """
        record = self.get_host_record(fqdn)
        deleted_ref = self.session.delete(record['_ref'])
        return deleted_ref

    # Txt record

    def create_txt_record(self, fqdn, text):
        """Create a txt record for the given *fqdn*.

        ;param str fqdn: the FQDN of a host
        :param str text: the text content of the record
        :return: an object reference to the new txt record
        :rtype: str
        """
        payload = {
            'text': text,
            'name': fqdn,
            'view': self.views['dns'],
        }
        ref = self.session.post('record:txt', json=payload)
        return ref

    def get_txt_record(self, fqdn, fields=None):
        """Get an existing txt record for the given *fqdn*.

        :param str fqdn: the FQDN of the host with a txt record
        :param list fields: additional txt record fields to return
        :return: the txt record optionally with additonal fields
        :rtype: dict
        :raises exceptions.NotFoundError: if there is no txt record associated
                                          with the given FQDN
        """
        params = {
            'name': fqdn,
            'view': self.views['dns'],
        }
        record = self.session.get('record:txt', params=params,
                                  return_fields=fields)
        try:
            return record[0]
        except IndexError:
            raise exceptions.NotFoundError('txt record', params['name'])

    def delete_txt_record(self, fqdn):
        """Delete the txt record of the given *fqdn*.

        :param str fqdn: an FQDN with a txt record
        :return: an object reference to the deleted txt record
        :rtype: str
        """
        record = self.get_txt_record(fqdn)
        deleted_ref = self.session.delete(record['_ref'])
        return deleted_ref

    # Host alias

    def create_host_alias(self, fqdn, alias):
        """Create a new *alias* for the given *fqdn*.

        :param str fqdn: the FQDN of an existing host
        :param str alias: the alias name
        :return: the updated host record
        :rtype: dict
        """
        record = self.get_host_record(fqdn, fields=('name', 'aliases'))
        aliases = record.get('aliases', [])
        # TODO: Know what happens when a duplicate alias is created
        aliases.append(alias)
        payload = {'aliases': aliases}
        updated_record = self.session.put(record['_ref'], json=payload)
        return updated_record

    def delete_host_alias(self, fqdn, alias):
        """Delete an *alias* from the host with the given *fqdn*.

        :param str fqdn: the FQDN of an existing host
        :param str alias: the alias name
        :return: the updated host record
        :rtype: dict
        """
        record = self.get_host_record(fqdn, fields=('name', 'aliases'))
        aliases = record.get('aliases', [])
        aliases.remove(alias)
        payload = {'aliases': aliases}
        updated_record = self.session.put(record['_ref'], json=payload)
        return updated_record

    # CNAME

    def create_cname_record(self, canonical, name):
        """Create a CNAME record for the given *canonical* name.

        :param str canonical: the canonical name of the host
        :param str name: the name of the new record
        :return: an object reference to the new CNAME record
        :rtype: str
        """
        payload = {
            'canonical': canonical,
            'name': name,
            'view': self.views['dns'],
        }
        ref = self.session.post('record:cname', json=payload)
        return ref

    def get_cname_record(self, name):
        """Get an existing CNAME record by *name*.

        :param str name: the name on the record
        :return: the CNAME record
        :rtype: dict
        """
        # FIXME: Why use a body instead of URL params for this one?
        payload = {'name': name}
        record = self.session.get('record:cname', json=payload)
        try:
            return record[0]
        except IndexError:
            raise exceptions.NotFoundError('CNAME record', payload['name'])

    def update_cname_record(self, canonical, name):
        """Update an existing CNAME record to point to the given *name*.

        :param str canonical: the canonical name of a host
        :param str name: the new name on the record
        :return: the updated CNAME record
        :rtype: dict
        """
        record = self.get_cname_record(name)
        payload = {'canonical': canonical}
        updated_record = self.session.put(record['_ref'], json=payload)
        return updated_record

    def delete_cname_record(self, name):
        """Delete an existing CNAME record by *name*.

        :param str name: the name on the record
        :return: an object reference to the deleted record
        :rtype: str
        """
        record = self.get_cname_record(name)
        deleted_ref = self.session.delete(record['_ref'])
        return deleted_ref

    # DHCP range

    def create_dhcp_range(self, start, end):
        """Create a new DHCP range from the given *start* and *end* addresses.

        :param str start: the IPv4 starting address
        :param str end: the IPv4 ending address
        :return: an object reference to the created record
        :rtype: str
        """
        payload = {
            'start_addr': start,
            'end_addr': end,
        }
        dhcp_range = self.session.post('range', json=payload)
        return dhcp_range

    def get_dhcp_range(self, start, end):
        """Get the DHCP range with the given *start* and *end* addresses.

        :param str start: the IPv4 starting address
        :param str end: the IPv4 ending address
        :return: the DHCP range
        :rtype: dict
        :raises exceptions.NotFoundError: if there is no DHCP range with the
                                          given *start* and *end* addresses
        """
        params = {
            'start_addr': start,
            'end_addr': end,
            'network_view': self.views['network'],
        }
        dhcp_range = self.session.get('range', params=params)
        try:
            return dhcp_range[0]
        except IndexError:
            raise exceptions.NotFoundError('DHCP range', (start, end))

    def delete_dhcp_range(self, start, end):
        """Delete the DHCP range with the given *start* and *end* addreeses.

        :param str start: the IPv4 starting address
        :param str end: the IPv4 ending address
        :return: an object reference to the deleted DHCP range
        :rtype: str
        """
        dhcp_range = self.get_dhcp_range(start, end)
        deleted_dhcp_range = self.session.delete(dhcp_range['_ref'])
        return deleted_dhcp_range

    # Network

    def create_network(self, network):
        """Create a new network.

        :param str network: the network in CIDR format
        :return: an object reference to the newly created network
        :rtype: str
        """
        payload = {
            'network': network,
            'network_view': self.views['network'],
        }
        network = self.session.post('network', json=payload)
        return network

    def get_networks(self, fields=None):
        """Get the networks with the given *fields*.

        *fields* is a mapping of field names to values. Each network must have
        the specified values for all fields to be considered a match. That is,
        each key-value pair in the dictionary represents a field=vlaue query,
        and all of the queries are AND'd together.

        :param dict fields: values of the fields each network must have to be
                            considered a match
        :return: all matching networks
        :rtype: list
        """
        networks = self.session.get('network', return_fields=fields)
        return networks

    def get_network(self, network, fields=None):
        """Get a network ammended with the given *fields*.

        :param str network: the network in CIDR format
        :param list fields: additional fields to return
        :return: the specified network ammended with the given fields
        :rtype: dict
        :raises exceptions.NotFoundError: if the given network cannot be found
        """
        params = {
            'network': network,
            'network_view': self.views['network'],
        }
        network = self.session.get('network', params=params,
                                   return_fields=fields)
        try:
            return network[0]
        except IndexError:
            raise exceptions.NotFoundError('network', params['network'])

    # TODO: Get rid of this method
    def get_network_extattrs(self, network):
        """Get the extattrs of the given *network*.

        :param str network: a network in CIDR format
        :return: the extattrs of the given *network*
        :rtype: dict
        """
        network = self.get_network(network, fields=('network', 'extattrs'))
        return {k: v['value'] for k, v in network['extattrs'].items()}

    def delete_network(self, network):
        """Delete the given network.

        :param str network: a network in CIDR format
        :return: an object reference to the deleted network
        :rtype: str
        """
        network = self.get_network(network)
        deleted_network = self.session.delete(network['_ref'])
        return deleted_network

    # Network containers

    def create_network_container(self, container):
        """Create a network container.

        :param str container: the container to create
        :return: an object reference to the newly created container
        :rtype: str
        """
        payload = {
            'network': container,
            'network_view': self.views['network'],
        }
        container = self.session.post('networkcontainer', json=payload)
        return container

    def get_network_container(self, container):
        """Get a network container.

        :param str container: a network container in CIDR format
        :return: a network container
        :rtype: dict
        :raises exceptions.NotFoundError: if the network container could not
                                          be found
        """
        params = {
            'network': container,
            'network_view': self.views['network']
        }
        container = self.session.get('networkcontainer', params=params)
        try:
            return container[0]
        except IndexError:
            raise exceptions.NotFoundError('network container', container)

    def delete_network_container(self, container):
        """Delete a network container.

        :param str container: a network container in CIDR format
        :return: an object reference to the deleted network container
        :rtype: str
        """
        container = self.get_network_container(container)
        deleted_ref = self.session.delete(container['_ref'])
        return deleted_ref

    # A records

    def get_a_records(self, fields=None):
        """Get all A-records ammeneded with the given *fields*.

        :param list fields: a list of additional fields to return
        :return: all A-reocrds
        :rtype: list
        """
        records = self.session.get('record:a', return_fields=fields)
        return records

    def get_a_records_by_field(self, field, value, fields=None):
        """Get the a records that have *value* for *field*.

        :param str field: the name of the field
        :param str value: the value the field must have
        :param list fields: additional fields to return
        :return: all matching A-records
        :rtype: list
        """
        params = {field: value}
        a_records = self.session.get('record:a', params=params,
                                     return_fields=fields)
        return a_records

    def get_a_record_by_ip(self, ip, fields=None):
        """Get the A-record with the given *ip*.

        :param str ip: the IPv4 address
        :param list fields: a list of additonal fields to return
        :return: the A-record with the given ip
        :rtype: dict
        :raises exceptions.NotFoundError: if no A-record with the given ip can
                                          be found
        """
        records = self.get_a_records_by_field(field='ipv4addr', value=ip,
                                              fields=fields)
        try:
            return records[0]
        except IndexError:
            raise exceptions.NotFoundError('A record', ip)

    def get_a_record_by_fqdn(self, fqdn, fields=None):
        """Get the A-record with the given *fqdn*.

        :param str fqdn: an FQDN
        :param list fields: a list of additional fields to return
        :return: the A-record with the given fqdn
        :rtype: dict
        :raises exceptions.NotFoundError: if no A-record with the given fqdn
                                          can be found
        """
        records = self.get_a_records_by_field(field='name', value=fqdn,
                                              fields=fields)
        try:
            return records[0]
        except IndexError:
            raise exceptions.NotFoundError('A record', fqdn)

    # Search utils

    def search(self, resource, query, fields=None):
        """Search for the given *resource* using the given *query*.

        :param str resource: a resource name (e.g. "record:host")
        :param dict query: fields and the values they must have
        :param list fields: additional fields to return
        :return: all host records matching the given query
        :rtype: list
        """
        params = {'view': self.views['dns']}
        params.update(query)
        records = self.session.get(resource, params=params,
                                   return_fields=fields)
        return records

    def search_host_records(self, query, fields=None):
        """Search for host records that match the given *query*.

        :param dict query: fields and the values they must have
        :param list fields: additional fields to return
        :return: all host records matching the given query
        :rtype: list
        """
        return self.search('record:host', query=query, fields=fields)

    def search_txt_records(self, query, fields=None):
        """Search for a txt record with the given *fqdn*.

        :param str fqdn: an FQDN
        :return: zero or more txt records with the given FQDN
        :rtype: list
        """
        return self.search('record:txt', query=query, fields=fields)

    # Specific gets

    def get_address_by_ip(self, ip):
        """Get the IPv4 address record with the given *ip*.

        :param str ip: an IPv4 address
        :return: an IPv4 address record
        :rtype: dict
        """
        params = {
            'ip_address': ip,
            'network_view': self.views['network'],
        }
        address = self.session.get('ipv4address', params=params)
        return address

    def get_host_ips(self, fqdn):
        """Get the IPv4 addresses associated with the given *fqdn*.

        :param str fqdn: an FQDN
        :return: the IPv4 addresses associated with the given *fqdn*
        :rtype: list
        """
        record = self.get_host_record(fqdn)
        return [e['ipv4addr'] for e in record['ipv4addrs']]

    def get_host_extattrs(self, fqdn):
        """Get the extattrs of the host record with the given *fqdn*.

        :param str fqdn: an FQDN
        :return: the extattrs of a host record
        :rtype: dict
        """
        record = self.get_host_record(fqdn)
        return {k: v['value'] for k, v in record['extattrs'].items()}

    def get_network_by_ip(self, ip):
        """Get the network in which the given *ip* exists.

        :param str ip: an IPv4 address
        :return: the network that contains the given ip
        :rtype: dict
        :raises exceptions.NotFoundError: if the IP address does not exist in
                                          any known networks
        """
        params = {
            'ip_address': ip,
            'network_view': self.views['network'],
        }
        network = self.session.get('ipv4address', params=params)
        try:
            return network[0]
        except IndexError:
            raise exceptions.NotFoundError('IP address', ip)

    def get_networks_by_extatts(self, attributes):
        """Get the networks with the given *attributes*.

        :param dict attributes: fields names and their values
        :return: all networks that have all the given fields and values
        :rtype: list
        """
        params = {'*{}'.format(k): v for k, v in attributes.items()}
        params['network_view'] = self.views['network']
        networks = self.session.get('network', params=params)
        return [n for n in networks if 'network' in n]

    def get_host_by_extattrs(self, attributes):
        """Get the host reocrds with the given *attributes*.

        :param dict attributes: fields names and their values
        :return: all host reocrds that have all the given fields and values
        :rtype: list
        """
        params = {'*{}'.format(k): v for k, v in attributes.items()}
        params['view'] = self.views['dns']
        record = self.session.get('record:host', params=params)
        return [r for r in record if 'name' in r]

    # High level actions

    def get_fqdn_from_ipv4address(self, address):
        """Get the FQDN from the given *address*.

        :param dict address: address record of the host
        :return: the FQDN associated with the given *address*
        :rtype: str
        """
        fqdn = address.get('dhcp_client_identifier')
        if not fqdn:
            leases = (r for r in address['objects'] if r.startswith('lease'))
            for lease in leases:
                record = self.session.get(lease, fields=['client_hostname'])
                fqdn = record['client_hostname']
                if fqdn:
                    break
        return fqdn

    def convert_lease_to_fixed_address(self, ip, create=True):
        """Convert a DHCP lease to a FixedAddress.

        If no host record for the given *ip* can be found, one is created if
        *create* is ``True``.

        :param str ip: the IPv4 address to convert to fixed
        :param bool create: whether to create a missing host record
        :return: the resulting host record
        :rtype: dict
        """
        address = self.get_address_by_ip(ip)
        try:
            host = self.get_host_record_by_mac(address['mac_address'])
        except exceptions.NotFoundError:
            if not create:
                raise
            fqdn = self.get_fqdn_from_ipv4address(address)
            host = self.create_host_record(ip, fqdn, is_dhcp=True)

        payload = {
            'configure_for_dhcp': True,
            'match_client': 'MAC_ADDRESS',
            'mac': address['mac_address'],
        }
        updated_record = self.session.put(host['_ref'], json=payload)
        return updated_record
