import dataclasses
from typing import Callable

import rospy
from duckietown_msgs.msg import DuckiematrixLinkDescription as DuckiematrixLinkDescriptionMsg


@dataclasses.dataclass
class DuckiematrixLinkDescription:
    matrix: str
    uri: str
    entity: str


def on_duckiematrix_connection_request(callback: Callable[[DuckiematrixLinkDescription], None]):
    def _internal_callback(msg):
        link = DuckiematrixLinkDescription(
            matrix=msg.matrix,
            uri=msg.uri,
            entity=msg.entity
        )
        callback(link)
    # setup subscriber
    rospy.Subscriber(
        _apply_namespace("duckiematrix/connect", 1),
        DuckiematrixLinkDescriptionMsg,
        _internal_callback,
        queue_size=1
    )


def _apply_namespace(name, ns_level):
    return '{:s}/{:s}'.format(
        _get_namespace(ns_level).rstrip('/'),
        name.strip('/')
    )


def _get_namespace(level):
    node_name = rospy.get_name()
    namespace_comps = node_name.lstrip('/').split('/')
    if level > len(namespace_comps):
        level = len(namespace_comps)
    return '/{:s}'.format('/'.join(namespace_comps[:level]))
