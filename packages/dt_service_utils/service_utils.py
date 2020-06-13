import json
import time
import zeroconf
import socket
import netifaces
from threading import Thread, Semaphore

from dt_class_utils import DTProcess

DT_SERVICE_TYPE = '_duckietown._tcp.local.'
DT_SERVICE_NAME = lambda name: f'DT::{name}::{socket.gethostname()}.{DT_SERVICE_TYPE}'
SERVICE_UPDATE_HZ = 1.0 / 10.0  # refresh once every 10 seconds


class DTService:

    def __init__(self, name, port=0, payload=None, paused=False):
        if DTProcess.get_instance() is None:
            print('ERROR: You are trying to create an object of type DTService before '
                  'an object of type DTProcess. DTService objects inherit the lifecycle '
                  'of the singleton instance of DTProcess. Create a DTProcess first.')
            exit(1)
        self._app = DTProcess.get_instance()
        self._zc = zeroconf.Zeroconf()
        self._name = name
        self._port = port
        self._payload = json.dumps((payload if payload is not None else dict())).encode()
        self._worker = Thread(target=self._work)
        self._active = not paused
        self._is_shutdown = False
        self._published_once = False
        self._network_semaphore = Semaphore(1)
        DTProcess.get_instance().register_shutdown_callback(self.shutdown)
        # start worker
        self._worker.start()

    def _work(self):
        while True:
            with self._network_semaphore:
                if self._is_shutdown:
                    return
                # ---
                srv = self._service_info()
                if self._active:
                    # register or update
                    try:
                        self._zc.update_service(srv)
                        self._published_once = True
                    except KeyError:
                        # updating failed because of KeyError, try registering first
                        try:
                            self._zc.register_service(srv)
                            self._published_once = True
                        except (zeroconf.NonUniqueNameException, BaseException):
                            pass
                    except BaseException:
                        pass
                else:
                    # unregister
                    try:
                        if self._published_once:
                            self._published_once = False
                            self._zc.unregister_service(srv)
                    except (KeyError, BaseException):
                        pass

            # sleep
            time.sleep(1.0 / SERVICE_UPDATE_HZ)

    def resume(self):
        if not self._active:
            self._app.logger.debug(f'Service {self._name} RESUMED!')
        self._active = True

    def pause(self):
        if self._active:
            self._app.logger.debug(f'Service {self._name} PAUSED!')
        self._active = False

    def yes(self):
        return self.resume()

    def no(self):
        return self.pause()

    def shutdown(self):
        self.pause()
        self._is_shutdown = True
        # unregister everything
        with self._network_semaphore:
            srv = self._service_info()
            try:
                if self._published_once:
                    self._zc.unregister_service(srv)
            except (KeyError, BaseException):
                pass

    def _service_info(self):
        return zeroconf.ServiceInfo(
            type_=DT_SERVICE_TYPE,
            name=DT_SERVICE_NAME(self._name),
            addresses=list(map(self._encode_ip4, self._get_all_ip4_addresses())),
            port=self._port,
            properties=b' ' + self._payload
        )

    @staticmethod
    def _get_all_ip4_addresses():
        ip_list = []
        for iface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addresses:
                for link in addresses[netifaces.AF_INET]:
                    ip_list.append(link['addr'])
        return ip_list

    @staticmethod
    def _encode_ip4(ip4):
        return socket.inet_pton(socket.AF_INET, ip4)
