import os
from typing import Optional

from .constants import \
    ENV_VAR_CONTROLLER_PROTOCOL, \
    ENV_VAR_CONTROLLER_HOSTNAME, \
    ENV_VAR_CONTROLLER_PORT, \
    DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PROTOCOL, \
    DEFAULT_MATRIX_CONTROLLER_DATA_IN_CONNECTOR_PORT, \
    DEFAULT_MATRIX_CONTROLLER_DATA_OUT_CONNECTOR_PORT


def get_matrix_protocol() -> Optional[str]:
    return os.environ.get(ENV_VAR_CONTROLLER_PROTOCOL,
                          DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PROTOCOL)


def get_matrix_hostname() -> Optional[str]:
    hostname = os.environ.get(ENV_VAR_CONTROLLER_HOSTNAME, None)
    if isinstance(hostname, str) and len(hostname.strip()) > 0:
        return hostname
    return None


def get_matrix_input_port() -> Optional[int]:
    return os.environ.get(ENV_VAR_CONTROLLER_PORT,
                          DEFAULT_MATRIX_CONTROLLER_DATA_IN_CONNECTOR_PORT)


def get_matrix_output_port() -> Optional[int]:
    return os.environ.get(ENV_VAR_CONTROLLER_PORT,
                          DEFAULT_MATRIX_CONTROLLER_DATA_OUT_CONNECTOR_PORT)
