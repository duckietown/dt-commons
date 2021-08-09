import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class CameraFrame(CBorMessage):
    format: str
    width: int
    height: int
    frame: bytes

    @classmethod
    def from_jpeg(cls, jpeg: bytes) -> 'CameraFrame':
        return CameraFrame("jpeg", 0, 0, jpeg)
