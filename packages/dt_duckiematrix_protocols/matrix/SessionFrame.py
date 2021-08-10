import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class SessionFrame(CBorMessage):
    session_id: int
    payload: bytes
