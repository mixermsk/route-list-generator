#!/usr/bin/env python3

import ipaddress
import json
import logging
import re
import shutil
import socket
import subprocess
import sys
import yaml

from netaddr import cidr_merge


class NetList():
    def __init__(self):
        self.networks = set()

    def add(self, cidr: str):
        self.networks.add(ipaddress.ip_network(cidr))

    def add_as(self, as_name: str):
        res = json.loads(subprocess.check_output(f'bgpq4 -j {as_name}'.split()))
        prefixes = [e['prefix'] for e in res['NN']]

        for pi, prefix in enumerate(prefixes, 1):
            logging.info("Processing prefix %s from AS %s (%d of %d)", prefix, as_name, pi, len(prefixes))
            self.add(prefix)

    def add_fqdn(self, fqdn: str):
        try:
            for cidr in {f'{res[4][0]}/32' for res in socket.getaddrinfo(fqdn, None, socket.AF_INET)}:
                self.add(cidr)
        except socket.gaierror:
            logging.error("Can`t resolve FQDN %s", fqdn)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO, stream=sys.stderr)

    if not shutil.which('bgpq4'):
        logging.fatal('You need bgpq4 to use this tool')
        sys.exit(1)

    if len(sys.argv) == 1:
        print(f'Usage: {sys.argv[0]} config_file.yaml')
        sys.exit(1)

    with open(sys.argv[1], 'rb') as conf_file:
        config = yaml.safe_load(conf_file)

    netlist = NetList()
    for i, entry in enumerate(config['routes'], 1):
        logging.info('Processing entry %s (%d of %d)', entry, i, len(config['routes']))

        if '.' not in entry:
            netlist.add_as(entry)
            continue

        if re.match(r'\d+\.\d+\.\d+\.\d+(/\d+)?', entry):
            if '/' not in entry:
                entry += '/32'

            netlist.add(entry)
            continue

        if re.match(r'[\w-]+\.\w+', entry):
            netlist.add_fqdn(entry)
            continue

        logging.warning('Unknown entry type %s', entry)

    source_count = len(netlist.networks)
    netlist.networks = set(cidr_merge([str(net) for net in netlist.networks]))
    logging.info('Merged %d to %d networks', source_count, len(netlist.networks))

    for net in netlist.networks:
        print(f'push "route { str(net.network) } { str(net.netmask) }"')
