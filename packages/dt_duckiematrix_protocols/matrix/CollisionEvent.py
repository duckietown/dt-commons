import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class CollisionEvent(CBorMessage):
    key1: str
    key2: str
