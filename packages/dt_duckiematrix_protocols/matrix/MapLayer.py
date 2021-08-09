import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class MapLayer(CBorMessage):
    name: str
    content: str
