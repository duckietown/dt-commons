from threading import Thread
from typing import Optional, Callable, Dict, Set

import zmq
from cbor2 import loads

from dt_duckiematrix_protocols.world import CBor2Message
from dt_duckiematrix_utils.configuration import \
    matrix_offers_connection, \
    get_matrix_avatar_name, \
    get_matrix_hostname, \
    get_matrix_port, \
    get_matrix_protocol


class DuckieMatrixSocket(Thread):

    def __init__(self, uri: str):
        super(DuckieMatrixSocket, self).__init__(daemon=True)
        self.uri: str = uri
        self.context: zmq.Context = zmq.Context()
        print(f"[duckiematrix-utils]: Establishing link to DATA connector at {uri}...")
        try:
            socket: zmq.Socket = self.context.socket(zmq.SUB)
            socket.connect(uri)
            self.socket = socket
        except BaseException as e:
            print(f"[duckiematrix-utils]: ERROR: {e}")
        self.decoders: Dict[str, type] = {}
        self.callbacks: Dict[str, Set[Callable]] = {}
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

    def subscribe(self, topic: str, msg_type: type, callback: Callable):
        if self.connected:
            # register topic -> msg_type mapping
            self.decoders[topic] = msg_type
            # register topic -> callback mapping
            if topic not in self.callbacks:
                self.callbacks[topic] = set()
            self.callbacks[topic].add(callback)
            # subscribe to topic
            self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        else:
            raise Exception("Socket not connected. Cannot subscribe to a topic.")

    def unsubscribe(self, topic: str, callback: Callable):
        if self.connected:
            # remove topic -> msg_type mapping
            if topic in self.decoders:
                del self.decoders[topic]
            # remove topic -> callback mapping
            if topic in self.callbacks:
                self.callbacks[topic].remove(callback)
                if len(self.callbacks[topic]) <= 0:
                    del self.callbacks[topic]
            # unsubscribe
            self.socket.setsockopt_string(zmq.UNSUBSCRIBE, topic)
        else:
            raise Exception("Socket not connected. Cannot unsubscribe a topic.")

    def publish(self, topic: str, message: CBor2Message):
        self.socket.send_multipart([topic.encode("ascii"), message.to_bytes()])

    def run(self) -> None:
        while not self.is_shutdown:
            topic, data = self.socket.recv_multipart()
            topic = topic.decode("ascii").trim()
            # noinspection PyUnresolvedReferences
            try:
                if topic in self.callbacks:
                    message = loads(data)
                    Decoder = self.decoders[topic]
                    message = Decoder(**message)
                    for cback in self.callbacks[topic]:
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
