from zeroconf import ServiceBrowser, Zeroconf
from collections import defaultdict
import json
import time

class FleetScanner:

    def __init__(self):
        self.type = "_duckietown._tcp.local."
        self.listener = DiscoverListener()
        self.zeroconf = Zeroconf()

    def scan(self):
        browser = ServiceBrowser(self.zeroconf, self.type, self.listener)
        time.sleep(1)
        return self.listener.get_all_online_devices()


class DiscoverListener():
    services = defaultdict(dict)
    supported_services = [
        'DT::ONLINE'
    ]

    def process_service_name(self, name):
        name = name.replace('._duckietown._tcp.local.', '')
        service_parts = name.split('::')
        if len(service_parts) != 3 or service_parts[0] != 'DT':
            return None, None
        name = '{}::{}'.format(service_parts[0], service_parts[1])
        server = service_parts[2]
        return name, server

    def remove_service(self, zeroconf, type, name):
        name, server = self.process_service_name(name)
        if not name:
            return
        del self.services[name][server]

    def add_service(self, zeroconf, type, sname):
        name, server = self.process_service_name(sname)
        if not name:
            return
        info = zeroconf.get_service_info(type, sname)
        txt = json.loads(list(info.properties.keys())[0].decode('utf-8')) \
            if len(info.properties) \
            else dict()
        self.services[name][server] = {
            'port': info.port,
            'txt': txt
        }

    def get_all_online_devices(self):
        hostnames = set()
        for service in self.supported_services:
            hostnames.update(self.services[service])
        return list(sorted(hostnames))
