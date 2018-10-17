Infoblox Python API CHANGELOG
=============================

1.7.1
---
* [Jimmy Campbell] - Fix `update_network_extattrs` to use `items()` instead of `iteritems()`

1.7.0
---
* [David Yoon] - Add the ability to change a comment for a network obj and fix a bug with extensible attributes

1.6.3
---
* [Frank Branham] - Fix pip 10 internal dependencies in setup.py

1.6.2
---
* [Phillip Ferentinos] - Add `get_dhcp_range` endpoint.
* [Phillip Ferentinos] - Add support to `Util` class for `delete_by_ref`
* [Phillip Ferentinos] - Add `create`, `get`, `delete` support for Fixed Addresses
* [Phillip Ferentinos] - Add `get_grid`, `restart_grid_services`, `get_pending_changes` support for Grid Members
* [Phillip Ferentinos] - Add `get_lease` support for DHCP Leases

1.6.1
---
* [Wei Lei] - Update hlinfoblox.py lease2fixed command.

1.6.0
---

* [Robert Grant] - Added 2.6 to the trove classifiers (we may as well get the credit!)
* [Robert Grant] - Added logging of failed requests via use of a custom Session class

1.5.1
-----

* [Phillip Ferentinos] - Add ability to search host records by their aliases

1.5.0
-----

* [Robert Grant] - Unifed the exception classes into a single hierarchy
* [Wei Lei] - Fixed `lease2fixed` in `hlinfobolx.py`

1.4.0
-----
* [Ryan Back] - Add retrieval of A record and CNAME by FQDN.

1.3.1
----

* [Wei Lei] - Change package name to be infoblox_cli

1.3.0
-----

 * [Jeff Tillotson] - Use request sessions
 * [James Johnson] - Add `lease2fixed` functionality inside new module `hlinfoblox.py`
 * [James Johnson] - Add `get_ipv4address_by_ip` functionality
 * [Wei Lei] - Add full test coverage for `cli.py`

1.2.0
-----

 * [Robert Grant] - Add command line interface for creating/deleting CNAMEs and HOST records
 * [Robert Grant] - Flesh out the project accessories (`setup.py`, etc.)

1.1.0
-----

 * [Jeffery Tillotson] - Add unit tests

1.0.0
-----

 * [Infoblox-Development] - Original project from [Github](https://github.com/Infoblox-Development/Infoblox-API-Python)
