import os
from typing import Optional

from dt_cli_utils import str_to_bool
from .constants import \
    ENV_VAR_CONTROLLER_CONNECT, \
    ENV_VAR_CONTROLLER_PROTOCOL, \
    ENV_VAR_CONTROLLER_HOSTNAME, \
    ENV_VAR_CONTROLLER_PORT, \
    ENV_VAR_AVATAR_NAME, \
    DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PROTOCOL, \
    DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PORT


def get_matrix_protocol() -> Optional[str]:
    return os.environ.get(ENV_VAR_CONTROLLER_PROTOCOL,
                          DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PROTOCOL)


def get_matrix_hostname() -> Optional[str]:
    return os.environ.get(ENV_VAR_CONTROLLER_HOSTNAME, None)


def get_matrix_port() -> Optional[int]:
    return os.environ.get(ENV_VAR_CONTROLLER_PORT, DEFAULT_MATRIX_CONTROLLER_DATA_CONNECTOR_PORT)


def get_matrix_avatar_name() -> Optional[str]:
    return os.environ.get(ENV_VAR_AVATAR_NAME, None)


def matrix_offers_connection() -> bool:
    value = os.environ.get(ENV_VAR_CONTROLLER_CONNECT, "no")
    return str_to_bool(value)
