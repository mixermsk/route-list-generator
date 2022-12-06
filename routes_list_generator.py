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
        self.networks = set()

    def add(self, cidr: str):
        new_net = ipaddress.ip_network(cidr)
        for net in self.networks:
            if net.num_addresses > 1 and new_net.subnet_of(net):
                return

            if new_net.num_addresses > 1 and new_net.supernet_of(net):
                self.networks.add(new_net)
                self.networks.remove(net)
                return

        self.networks.add(new_net)

    def __iter__(self):
        for net in self.networks:
            yield net

    def add_as(self, as_name: str):
        res = json.loads(subprocess.check_output(f'bgpq4 -j {as_name}'.split()))
        for prefix in [e['prefix'] for e in res['NN']]:
            self.add(prefix)

    def add_fqdn(self, fqdn: str):
        for cidr in {f'{res[4][0]}/32' for res in socket.getaddrinfo(fqdn, None, socket.AF_INET)}:
            self.add(cidr)


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

            netlist.add(entry)
            continue

        if re.match(r'\w+\.\w+', entry):
            netlist.add_fqdn(entry)
            continue

        print(f'Unknown entry type {entry}', file=sys.stderr)

    for _net in netlist:
        print(f'push "route {_net.network_address} {_net.netmask}"')
