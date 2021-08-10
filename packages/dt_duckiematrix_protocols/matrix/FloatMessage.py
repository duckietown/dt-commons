import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class FloatMessage(CBorMessage):
    value: float
