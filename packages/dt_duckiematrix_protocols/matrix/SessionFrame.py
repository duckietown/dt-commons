import dataclasses
from enum import IntEnum

from dt_duckiematrix_protocols import CBorMessage


class SessionFrameType(IntEnum):
    SESSION_START = 0
    SESSION_END = 1
    SESSION_ERROR = 2
    SESSION_OK = 3
    SESSION_LAYER_UPDATE = 4
    LAYER_UPDATE = 5
    SENSOR_DATA = 6
    COLLISION_EVENT = 7


@dataclasses.dataclass
class SessionFrame(CBorMessage):
    type: int
    session_id: int
    payload: bytes
