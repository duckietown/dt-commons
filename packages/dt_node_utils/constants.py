import os
from enum import Enum
from pathlib import Path
from typing import Any

DIAGNOSTICS_ENABLED = os.environ.get('DT_DIAGNOSTICS', '1').lower() in \
                      ['1', 'true', 'yes', 'enabled']

NODE_CONFIG_DIR = Path(os.environ.get('DT_NODE_CONFIG_DIR', '/data/config/nodes'))
try:
    NODE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print(f"WARNING: Permission denied to create directory {NODE_CONFIG_DIR}. Things might not work as expected.")


class TopicDirection(Enum):
    INBOUND = 0
    OUTBOUND = 1


class NodeType(Enum):
    GENERIC = 0
    DRIVER = 1
    PERCEPTION = 2
    CONTROL = 3
    PLANNING = 4
    LOCALIZATION = 5
    MAPPING = 6
    SWARM = 7
    BEHAVIOR = 8
    VISUALIZATION = 9
    INFRASTRUCTURE = 10
    COMMUNICATION = 11
    DIAGNOSTICS = 12
    CALIBRATION = 13
    DEBUG = 20


TopicType = NodeType


class ParamType(Enum):
    UNKNOWN = 0
    STRING = 1
    INT = 2
    FLOAT = 3
    BOOL = 4
    LIST = 5
    DICT = 6

    @classmethod
    def to_type(cls, t: 'ParamType'):
        return {
            ParamType.UNKNOWN: lambda x: x,
            ParamType.STRING: str,
            ParamType.INT: int,
            ParamType.FLOAT: float,
            ParamType.BOOL: bool,
            ParamType.LIST: lambda x: x,
            ParamType.DICT: lambda x: x
        }[t]

    @classmethod
    def to_enum(cls, t: Any):
        return {
            str: ParamType.STRING,
            int: ParamType.INT,
            float: ParamType.FLOAT,
            bool: ParamType.BOOL,
            list: ParamType.LIST,
            tuple: ParamType.LIST,
            dict: ParamType.DICT
        }[t]

    @classmethod
    def parse(cls, param_type: 'ParamType', param_value: Any):
        if param_value is None:
            return None
        if not isinstance(param_type, ParamType):
            raise ValueError("Argument 'param_type' must be of type ParamType. "
                             "Got %s instead." % str(type(param_type)))
        # ---
        return cls.to_type(param_type)(param_value)

    @classmethod
    def guess_type(cls, param_value) -> 'ParamType':
        try:
            enum: ParamType = cls.to_enum(type(param_value))
        except KeyError:
            return cls.UNKNOWN
        # ---
        return enum


class NodeHealth(Enum):
    UNKNOWN = 0
    STARTING = 5
    STARTED = 6
    HEALTHY = 10
    WARNING = 20
    ERROR = 30
    FATAL = 40
