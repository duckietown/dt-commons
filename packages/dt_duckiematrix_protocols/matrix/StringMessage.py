import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class StringMessage(CBorMessage):
    value: str
