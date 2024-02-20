import os
import sys
import time
import logging
import signal
from typing import List, Callable, Tuple

from .app_status import AppStatus
from dt_module_utils import set_module_healthy

Args, KWargs = Tuple, dict


class DTProcess(object):

    __instance__ = None

    def __init__(self, name: str, catch_signals: bool = True):
        if DTProcess.__instance__ is not None:
            print('ERROR: You are trying to create two instances of type DTProcess. '
                  'This is not allowed, only one instance is allowed per process.')
            exit(1)
        self._status: AppStatus = AppStatus.INITIALIZING
        self._sigint_counter: int = 0
        self._app_name: str = type(self).__name__ if not name else name
        self._shutdown_cbs: List[Tuple[Callable, Args, KWargs]] = []
        self._catch_signals: bool = catch_signals
        self._is_debug: bool = False
        self._start_time: float = time.time()
        # define logger
        logging.basicConfig()
        self.logger: logging.Logger = logging.getLogger(self._app_name)
        self.logger.setLevel(logging.INFO)
        if 'DEBUG' in os.environ and os.environ['DEBUG'].lower() in ['true', 'yes', '1']:
            self.logger.setLevel(logging.DEBUG)
            self._is_debug = True
        # register signal handlers
        if self._catch_signals:
            signal.signal(signal.SIGINT, self._on_sigint)
        # store singleton
        DTProcess.__instance__ = self
        self.status: AppStatus = AppStatus.RUNNING

    @staticmethod
    def get_instance() -> 'DTProcess':
        return DTProcess.__instance__

    @property
    def status(self):
        return self._status

    @property
    def is_debug(self):
        return self._is_debug

    @property
    def start_time(self):
        return self._start_time

    @property
    def uptime(self):
        return time.time() - self._start_time

    @property
    def name(self):
        return self._app_name

    @status.setter
    def status(self, status):
        if not isinstance(status, AppStatus):
            raise ValueError(
                "Trying to set App status to object of type {0}, "
                "expected type 'dt_class_utils.AppStatus' instead.".format(str(type(status)))
            )
        self.logger.info('App status changed [%s] -> [%s]' % (self._status.name, status.name))
        self._status = status
        # set health
        if status == AppStatus.RUNNING:
            set_module_healthy()

    @property
    def is_shutdown(self):
        return self._status == AppStatus.TERMINATING

    def shutdown(self, reason: str = None):
        if reason:
            self.logger.info('Shutdown requested: %s' % reason)
        if self.is_shutdown:
            return
        self._status = AppStatus.TERMINATING
        for cb, args, kwargs in self._shutdown_cbs:
            cb(*args, **kwargs)

    def kill(self):
        self._status = AppStatus.KILLING
        sys.exit(-1000)

    def register_shutdown_callback(self, cb, *args, **kwargs):
        if not self._catch_signals:
            raise ValueError('Cannot register shutdown callback if signal catching is disabled.')
        if callable(cb):
            self._shutdown_cbs.append((cb, args, kwargs))

    # noinspection PyUnusedLocal
    def _on_sigint(self, sig, frame):
        if self._sigint_counter == 0:
            self._sigint_counter = 1
            self.logger.info('Shutdown request received! Gracefully terminating....')
            self.logger.info('Press [Ctrl+C] three times to force kill.')
            self.shutdown()
        elif self._sigint_counter == 3:
            self.logger.info('Escalating to SIGKILL.')
            self.kill()
        else:
            self._sigint_counter += 1
