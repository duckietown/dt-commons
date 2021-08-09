from threading import Thread
from typing import Optional, Callable, Dict, Set

import zmq
from cbor2 import loads

from dt_duckiematrix_protocols import CBorMessage
from dt_duckiematrix_utils.configuration import \
    matrix_offers_connection, \
    get_matrix_hostname, \
    get_matrix_input_port, \
    get_matrix_output_port, \
    get_matrix_protocol


class DuckieMatrixSocket(Thread):

    def __init__(self, data_in_uri: str, data_out_uri: str):
        super(DuckieMatrixSocket, self).__init__(daemon=True)
        self.data_in_uri: str = data_in_uri
        self.data_out_uri: str = data_out_uri
        self.context: zmq.Context = zmq.Context()
        # socket IN
        print(f"[duckiematrix-utils]: Establishing link to DATA IN connector "
              f"at {data_in_uri}...")
        try:
            socket: zmq.Socket = self.context.socket(zmq.SUB)
            socket.connect(data_in_uri)
            self.in_socket = socket
        except BaseException as e:
            print(f"[duckiematrix-utils]: ERROR: {e}")
        # socket IN
        print(f"[duckiematrix-utils]: Establishing link to DATA OUT connector "
              f"at {data_out_uri}...")
        try:
            socket: zmq.Socket = self.context.socket(zmq.PUB)
            socket.connect(data_out_uri)
            self.out_socket = socket
        except BaseException as e:
            print(f"[duckiematrix-utils]: ERROR: {e}")
        # ---
        self.decoders: Dict[str, type] = {}
        self.callbacks: Dict[str, Set[Callable]] = {}
        self.is_shutdown = False

    @property
    def connected(self) -> bool:
        return self.in_socket is not None and self.out_socket is not None

    def release(self):
        # close sockets
        sockets = {
            self.data_in_uri: self.in_socket,
            self.data_out_uri: self.out_socket,
        }
        for uri, socket in sockets.items():
            if socket is not None:
                try:
                    socket.disconnect(uri)
                except Exception as e:
                    print(f"[duckiematrix-utils]: ERROR: {e}")
                try:
                    socket.close()
                except Exception as e:
                    print(f"[duckiematrix-utils]: ERROR: {e}")

    def shutdown(self, block: bool = True):
        self.is_shutdown = True
        self.release()
        if block:
            self.join()

    def subscribe(self, topic: str, msg_type: type, callback: Callable):
        if self.connected:
            # register topic -> msg_type mapping
            self.decoders[topic] = msg_type
            # register topic -> callback mapping
            if topic not in self.callbacks:
                self.callbacks[topic] = set()
            self.callbacks[topic].add(callback)
            # subscribe to topic
            self.in_socket.setsockopt_string(zmq.SUBSCRIBE, topic)
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
            self.in_socket.setsockopt_string(zmq.UNSUBSCRIBE, topic)
        else:
            raise Exception("Socket not connected. Cannot unsubscribe a topic.")

    def publish(self, topic: str, message: CBorMessage):
        self.out_socket.send_multipart([topic.encode("ascii"), message.to_bytes()])

    def run(self) -> None:
        while not self.is_shutdown:
            topic, data = self.in_socket.recv_multipart()
            topic = topic.decode("ascii").strip()
            # noinspection PyUnresolvedReferences
            if topic in self.callbacks:
                message = loads(data)
                Decoder = self.decoders[topic]
                message = Decoder(**message)
                for cback in self.callbacks[topic]:
                    cback(message)

    @classmethod
    def create(cls) -> Optional['DuckieMatrixSocket']:
        if not matrix_offers_connection():
            print("[duckiematrix-utils]: ERROR: No connection offered by the matrix")
            return None
        # get hostname and port of the connector
        conn_proto = get_matrix_protocol()
        conn_host = get_matrix_hostname()
        in_conn_port = get_matrix_input_port()
        out_conn_port = get_matrix_output_port()
        if conn_host is None:
            print(f"[duckiematrix-utils]: ERROR: No connector host provided")
            return None
        # create socket
        uris = []
        for conn_port in [in_conn_port, out_conn_port]:
            if conn_proto == "icp":
                uri = f"{conn_proto}://{conn_host}"
            else:
                uri = f"{conn_proto}://{conn_host}:{conn_port}"
            uris.append(uri)
        # ---
        return DuckieMatrixSocket(*uris)
