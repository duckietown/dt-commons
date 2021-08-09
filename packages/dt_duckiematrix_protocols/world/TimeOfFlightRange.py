import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class TimeOfFlightRange(CBorMessage):
    range: float
