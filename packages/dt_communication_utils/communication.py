import threading
from typing import Callable, Union

import lcm
import logging

from hashlib import sha256
from ipaddress import IPv4Address

logging.basicConfig()


class DTCommunicationGroup(object):

    IP_NETWORK = "239.255.0.0/20"
    DEFAULT_PORT = "7667"
    DEFAULT_CHANNEL = "/__default__"
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
    def id(self):
        return self._id

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

    def Subgroup(self, name: str, loglevel: int = None):
        if loglevel is None:
            loglevel = self._logger.level
        return DTCommunicationSubGroup(self, name, loglevel)

    def Publisher(self):
        pub = DTCommunicationGroupPublisher(self, self.DEFAULT_CHANNEL)
        self.add_publisher(pub)
        return pub

    def Subscriber(self, callback: Callable):
        sub = DTCommunicationGroupSubscriber(self, self.DEFAULT_CHANNEL, callback)
        self.add_subscriber(sub)
        return sub

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


class DTCommunicationSubGroup(object):

    def __init__(self, group: DTCommunicationGroup, name: str, loglevel: int = logging.WARNING):
        self._group = group
        self._name = '/' + name.strip('/')
        self._is_shutdown = False
        self._logger = logging.getLogger(f'CommSubGroup[#{self._group.id}{self._name}]')
        self._logger.setLevel(loglevel)
        self._publishers = set()
        self._subscribers = set()

    @property
    def handler(self):
        return self._group.handler

    @property
    def is_shutdown(self):
        return self._is_shutdown

    def Publisher(self):
        pub = DTCommunicationGroupPublisher(self, self._name)
        self.add_publisher(pub)
        return pub

    def Subscriber(self, callback: Callable):
        sub = DTCommunicationGroupSubscriber(self, self._name, callback)
        self.add_subscriber(sub)
        return sub

    def add_publisher(self, publisher: 'DTCommunicationGroupPublisher'):
        self._publishers.add(publisher)
        self._group.add_publisher(publisher)

    def add_subscriber(self, subscriber: 'DTCommunicationGroupSubscriber'):
        self._subscribers.add(subscriber)
        self._group.add_subscriber(subscriber)

    def remove_publisher(self, publisher: 'DTCommunicationGroupPublisher'):
        self._publishers.remove(publisher)
        self._group.remove_publisher(publisher)

    def remove_subscriber(self, subscriber: 'DTCommunicationGroupSubscriber'):
        self._subscribers.remove(subscriber)
        self._group.remove_subscriber(subscriber)

    def shutdown(self):
        # shutdown all publishers
        for pub in self._publishers:
            pub.shutdown()
        # shutdown all subscribers
        for sub in self._subscribers:
            sub.shutdown()
        # ---
        self._is_shutdown = True


class DTCommunicationGroupPublisher(object):

    def __init__(self, group: Union[DTCommunicationGroup, DTCommunicationSubGroup], topic: str):
        self._group = group
        self._topic = topic

    def publish(self, msg: bytes):
        self._group.handler.publish(self._topic, msg)

    def shutdown(self):
        self._group.remove_publisher(self)


class DTCommunicationGroupSubscriber(object):

    def __init__(self, group: Union[DTCommunicationGroup, DTCommunicationSubGroup],
                 topic: str, callback: Callable):
        self._group = group
        self._topic = topic
        self._callback = callback
        self._subscription_handler = self._group.handler.subscribe(self._topic, self._callback)

    def shutdown(self):
        self._group.handler.unsubscribe(self._subscription_handler)
        self._group.remove_subscriber(self)

    def __inner_callback__(self, topic, data):
        pass
