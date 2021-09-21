from typing import Callable

import rospy

from duckietown_msgs.msg import DuckiematrixConnectorsDescription

from .socket import DuckieMatrixSocket


def on_duckiematrix_connection_request(callback: Callable[[str, str, str], None]):
    def _internal_callback(msg):
        callback(msg.name, msg.data_in_uri, msg.data_out_uri)
    # setup subscriber
    rospy.Subscriber(
        _apply_namespace("duckiematrix/connect", 1),
        DuckiematrixConnectorsDescription,
        _internal_callback,
        queue_size=1
    )
    # if there is already a request pending, (maybe from env variables), trigger a callback
    request = DuckieMatrixSocket.get_pending_connection_request()
    if request is not None:
        callback("local", request.data_in_uri, request.data_out_uri)


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
