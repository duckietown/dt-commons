import dataclasses

from dt_duckiematrix_protocols.world import CBor2Message


@dataclasses.dataclass
class CameraFrame(CBor2Message):
    format: str
    width: int
    height: int
    frame: bytes
