import threading
from typing import Callable

import lcm
import logging

from hashlib import sha256
from ipaddress import IPv4Address

logging.basicConfig()


class DTCommunicationGroup(object):

    IP_NETWORK = "239.255.0.0/20"
    DEFAULT_PORT = "7667"
    LCM_HEARTBEAT_HZ = 1

    def __init__(self, name: str, ttl: int = 1, loglevel: int = logging.WARNING):
        self._name = name
        self._ttl = ttl
        self._id = self._get_group_id()
        self._url = self._get_url(self.DEFAULT_PORT)
        self._is_shutdown = False
        self._logger = logging.getLogger(f'CommGroup[#{self._id}]')
        self._logger.setLevel(loglevel)
        self._publishers = set()
        self._subscribers = set()
        # create LCM handler
        self._logger.debug(f'Creating LCM handler on URL: `{self._url}`')
        self._lcm = lcm.LCM(self._url)
        self._mailman = threading.Thread(target=self._spin)
        self._mailman.start()

    @property
    def name(self):
        return self._name

    @property
    def ttl(self):
        return self._ttl

    @property
    def handler(self):
        return self._lcm

    @property
    def is_shutdown(self):
        return self._is_shutdown

    def Publisher(self, topic: str):
        return DTCommunicationGroupPublisher(self, topic)

    def Subscriber(self, topic: str, callback: Callable):
        return DTCommunicationGroupSubscriber(self, topic, callback)

    def add_publisher(self, publisher: 'DTCommunicationGroupPublisher'):
        self._publishers.add(publisher)

    def add_subscriber(self, subscriber: 'DTCommunicationGroupSubscriber'):
        self._subscribers.add(subscriber)

    def remove_publisher(self, publisher: 'DTCommunicationGroupPublisher'):
        self._publishers.remove(publisher)

    def remove_subscriber(self, subscriber: 'DTCommunicationGroupSubscriber'):
        self._subscribers.remove(subscriber)

    def shutdown(self):
        # shutdown all publishers
        for pub in self._publishers:
            pub.shutdown()
        # shutdown all subscribers
        for sub in self._subscribers:
            sub.shutdown()
        # ---
        self._is_shutdown = True

    def _get_url(self, port):
        return f"udpm://{self._get_group_ip()}:{port}?ttl={self.ttl}"

    def _get_group_id(self):
        _, masklen = self.IP_NETWORK.split('/')
        range_len = 2 ** (32 - int(masklen))
        return int(sha256(self.name.encode('utf-8')).hexdigest(), 16) % range_len

    def _get_group_ip(self):
        base_ip, _ = self.IP_NETWORK.split('/')
        base_ip = IPv4Address(base_ip)
        ip_id = self._get_group_id()
        group_ip = base_ip + ip_id
        return group_ip

    def _spin(self):
        period = (1.0 / self.LCM_HEARTBEAT_HZ) * 1000
        try:
            while not self.is_shutdown:
                self._lcm.handle_timeout(period)
        except KeyboardInterrupt:
            pass


class DTCommunicationGroupPublisher(object):

    def __init__(self, group: DTCommunicationGroup, topic: str):
        self._group = group
        self._topic = topic
        self._group.add_publisher(self)

    def publish(self, msg: bytes):
        self._group.handler.publish(self._topic, msg)

    def shutdown(self):
        self._group.remove_publisher(self)


class DTCommunicationGroupSubscriber(object):

    def __init__(self, group: DTCommunicationGroup, topic: str, callback: Callable):
        self._group = group
        self._topic = topic
        self._callback = callback
        self._subscription_handler = self._group.handler.subscribe(self._topic, self._callback)
        self._group.add_subscriber(self)

    def shutdown(self):
        self._group.handler.unsubscribe(self._subscription_handler)
        self._group.remove_subscriber(self)

    def __inner_callback__(self, topic, data):
        pass
