# route-list-generator
Utility for generating OpenVPN route-lists from AS names, FQDNs and CIDRs. Python 3.7+ and [bgpq4]( https://github.com/bgp/bgpq4) are required.

## Config example:
```
routes:
  - some-site.tld
  - AS-SOMECOMPANY
  - 1.1.1.0/24
  - 1.2.3.4
```

## Usage
Just put result into file and include it to your OpenVPN config.

