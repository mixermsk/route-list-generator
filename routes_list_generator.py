#!/usr/bin/env python3

import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import yaml


class NetList():
    def __init__(self):
        self.networks = {}

    def add(self, block: str, cidr: str):
        new_net = ipaddress.ip_network(cidr)

        if block not in self.networks:
            self.networks[block] = set()

        for _block, _networks in self.networks.items():
            for _net in _networks:
                if _net.num_addresses > 1 and new_net.subnet_of(_net):
                    return

                if new_net.num_addresses > 1 and new_net.supernet_of(_net):
                    self.networks[block].add(new_net)
                    _networks[_block].remove(_net)
                    return

        self.networks[block].add(new_net)

    def add_as(self, as_name: str):
        res = json.loads(subprocess.check_output(f'bgpq4 -j {as_name}'.split()))
        for prefix in [e['prefix'] for e in res['NN']]:
            self.add(as_name, prefix)

    def add_fqdn(self, fqdn: str):
        for cidr in {f'{res[4][0]}/32' for res in socket.getaddrinfo(fqdn, None, socket.AF_INET)}:
            self.add(fqdn, cidr)


if __name__ == '__main__':
    if not shutil.which('bgpq4'):
        print('You need bgpq4 to use this tool', file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 1:
        print(f'Usage: {sys.argv[0]} config_file.yaml')
        sys.exit(1)

    with open(sys.argv[1], 'rb') as conf_file:
        config = yaml.safe_load(conf_file)

    netlist = NetList()
    for entry in config['routes']:
        if entry.startswith('AS') and '.' not in entry:
            netlist.add_as(entry)
            continue

        if re.match(r'\d+\.\d+\.\d+\.\d+(/\d+)?', entry):
            if '/' not in entry:
                entry += '/32'

            netlist.add(entry, entry)
            continue

        if re.match(r'[\w-]+\.\w+', entry):
            netlist.add_fqdn(entry)
            continue

        print(f'Unknown entry type {entry}', file=sys.stderr)

    for _block, _networks in netlist.networks.items():
        if _networks:
            print(f'# {_block}')
        for net in _networks:
            print(f'push "route {net.network_address} {net.netmask}"')
