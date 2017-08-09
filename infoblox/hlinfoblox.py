# -*- coding: utf-8 -*-
#
# Copyright stuff
#
# License stuff
#

import json
from .infoblox import Infoblox, InfobloxGeneralException, Util

# import more stuff


class HighLevelInfobloxActions(object):

    """ Implements the following high level infoblox actions
    convert_lease_to_fixed_address
    """

    def __init__(self,
                 iba_ipaddr,
                 iba_user,
                 iba_password,
                 iba_wapi_version,
                 iba_dns_view,
                 iba_network_view,
                 iba_verify_ssl=False):
        """ Class initialization method
        :param iba_ipaddr: IBA IP address of management interface
        :param iba_user: IBA user name
        :param iba_password: IBA user password
        :param iba_wapi_version: IBA WAPI version (example: 1.0)
        :param iba_dns_view: IBA default view
        :param iba_network_view: IBA default network view
        :param iba_verify_ssl: IBA SSL certificate validation (example: False)
        """
        self.iba_host = iba_ipaddr
        self.iba_user = iba_user
        self.iba_password = iba_password
        self.iba_wapi_version = iba_wapi_version
        self.iba_dns_view = iba_dns_view
        self.iba_network_view = iba_network_view
        self.iba_verify_ssl = iba_verify_ssl

        self.api = Infoblox(iba_ipaddr, iba_user, iba_password,
                            iba_wapi_version, iba_dns_view, iba_network_view,
                            iba_verify_ssl)

    def convert_lease_to_fixed_address(self, address, fqdn=None,
                                       confirm=False):
        """Convert a DHCP-assigned leased address to a fixed address.
        :param address: IP Address to be converted
        :param fqdn: Fully qualified domain name for host if we cannot
            determine it from the lease information.
        :param confirm: Confirm that you really want to do this.
        """

        # Get our host information
        ipv4address_record = self.api.get_ipv4address_by_ip(address, fields=[
            'dhcp_client_identifier',
            'mac_address',
            'names',
            'objects'])
        print("IPV4 Address Record [%s]" % (ipv4address_record))

        # Try to find a record:host for the host we found.
        names = ipv4address_record['names']
        if names is None and fqdn is None:
            raise(InfobloxGeneralException(
                "Cannot determine fqdn for [%s]" % (address)))

        mac = ipv4address_record['mac_address']
        print("mac [%s]" % (mac))
        if mac is None or mac is '':
            raise(InfobloxGeneralException(
                "Cannot determine mac for [%s]" % (address)))

        if fqdn is None:
            fqdn = self._guess_fqdn(address, ipv4address_record)

        if not names:
            self._create_host_record(address, fqdn, mac)
     
        print("this-is-fqdn [%s]" % fqdn)
        print("this-is-names [%s]" % names)
        # If we found names associated with the address then
        # we can use those names to find record:host objects
        # and convert them to fixed.
        for name in names:
            print("Host Name [%s]" % (name))
            host_record = self.api.get_host(name, notFoundFail=False)
            print("Host Record [%s]" % (host_record))

            if host_record:
                dhcp_cfg = str(host_record['ipv4addrs'][0]['configure_for_dhcp'])
            
                if dhcp_cfg == 'True':
                    print(" Host record for [%s] already exist" % host_record)
                    break

                else: 
                    print("    Updating host record - converting lease to fixedaddress")
                    for host_host_ipv4addr in host_record['ipv4addrs']:
                        fields = {
                            'configure_for_dhcp': True,
                            'match_client': 'MAC_ADDRESS',
                            'mac': mac
                        }
                        self.api.update_record(host_record,
                                           fields=fields,
                                           confirm=confirm)
                    break
            else:
                print("   Creating host record - Converting lease to fixedaddress")
                payload = {
                    'name': fqdn,
                    'ipv4addrs' : [{'ipv4addr': address,
                                    'configure_for_dhcp': True,
                                    'mac': mac}]
                }
                uri = 'record:host'
                fields=''
                status_code = self.api.util.post(uri, payload, fields)
                break


    def _create_host_record(self, address, fqdn, mac):
        if fqdn is None:
            raise(InfobloxGeneralException(
                "Cannot determine fqdn for new HOST Record for [%s]" %
                (address)))
        payload = {'name': fqdn,
                   'view': self.iba_dns_view,
                   'ipv4addrs': [{'ipv4addr': address,
                                  'configure_for_dhcp': True,
                                  'match_client': 'MAC_ADDRESS',
                                  'mac': mac
                                  }]}
        print("host_data [%s]" % (payload))
        self.api.create_host_record(address, fqdn,
                                    payload=payload)

    def _guess_fqdn(self, address, ipv4address_record):
        """Try to figure out an address' fqdn.
        :param address: IP v4 address or NET v4 address in CIDR format
        :return: None on failure else fqdn.
        :rtype string:
        """

        if 'dhcp_client_identifier' in ipv4address_record:
            return ipv4address_record['dhcp_client_identifier']

        for ref in ipv4address_record['objects']:
            if ref.startswith('lease/'):
                lease_ref = ref
                print("Lease Reference [%s]" % (lease_ref))
                lease_record = self.api.util.get(lease_ref,
                                                 fields=['client_hostname'])
                print("Lease Record [%s]" % (lease_record))

                if 'client_hostname' in lease_record:
                    return lease_record['client_hostname']

        return None
