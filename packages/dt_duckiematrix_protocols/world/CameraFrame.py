import dataclasses

from dt_duckiematrix_protocols.world import CBor2Message


@dataclasses.dataclass
class CameraFrame(CBor2Message):
    format: str
    width: int
    height: int
    frame: bytes

    @classmethod
    def from_jpeg(cls, jpeg: bytes) -> 'CameraFrame':
        return CameraFrame("jpeg", 0, 0, jpeg)
