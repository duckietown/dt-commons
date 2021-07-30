from threading import Thread
from typing import Optional, Callable

import zmq
from google import protobuf

from dt_duckiematrix_protocols.WorldMessageProto_pb2 import WorldMessageProto
from dt_duckiematrix_utils.configuration import matrix_offers_connection, get_matrix_avatar_name, \
    get_matrix_hostname, get_matrix_port, get_matrix_protocol


class DuckieMatrixSocket(Thread):

    def __init__(self, uri: str):
        super(DuckieMatrixSocket, self).__init__(daemon=True)
        self.uri: str = uri
        self.context: zmq.Context = zmq.Context()
        print(f"[duckiematrix-utils]: Establishing link to DATA connector at {uri}...")
        self.socket: zmq.Socket = self.context.socket(zmq.SUB)
        self.socket.connect(uri)
        self.callbacks = set()
        self.is_shutdown = False

    @property
    def connected(self) -> bool:
        return self.socket is not None

    def release(self):
        if self.socket is not None:
            try:
                self.socket.disconnect(self.uri)
            except Exception as e:
                print(f"[duckiematrix-utils]: ERROR: {e}")
            try:
                self.socket.close()
            except Exception as e:
                print(f"[duckiematrix-utils]: ERROR: {e}")

    def shutdown(self):
        self.is_shutdown = True

    def subscribe(self, topic: str, callback: Callable):
        if self.connected:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
            self.callbacks.add(callback)

    def unsubscribe(self, topic: str, callback: Callable):
        if self.connected:
            self.socket.setsockopt_string(zmq.UNSUBSCRIBE, topic)
            self.callbacks.remove(callback)

    def publish(self, topic: str, message: WorldMessageProto):
        self.socket.send_multipart([topic, message.SerializeToString()])

    def run(self) -> None:
        while not self.is_shutdown:
            _, data = self.socket.recv_multipart()
            # noinspection PyUnresolvedReferences
            try:
                message = WorldMessageProto()
                message.ParseFromString(data)
                for cback in self.callbacks:
                    cback(message)
            except protobuf.message.DecodeError as e:
                print(f"[duckiematrix-utils]: ERROR: {e}")

    @classmethod
    def create(cls) -> Optional['DuckieMatrixSocket']:
        if not matrix_offers_connection():
            print("[duckiematrix-utils]: ERROR: No connection offered by the matrix")
            return None
        # get hostname and port of the connector
        conn_proto = get_matrix_protocol()
        conn_host = get_matrix_hostname()
        conn_port = get_matrix_port()
        if conn_host is None:
            print(f"[duckiematrix-utils]: ERROR: No connector host provided")
            return None
        # get avatar name in the matrix
        conn_avatar = get_matrix_avatar_name()
        if conn_avatar is None:
            print(f"[duckiematrix-utils]: ERROR: No avatar name provided")
            return None
        # create socket
        if conn_proto == "icp":
            uri = f"{conn_proto}://{conn_host}"
        else:
            uri = f"{conn_proto}://{conn_host}:{conn_port}"
        return DuckieMatrixSocket(uri)
