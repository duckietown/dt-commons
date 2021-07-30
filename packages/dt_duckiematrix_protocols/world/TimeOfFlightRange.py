import dataclasses

from dt_duckiematrix_protocols.world import CBor2Message


@dataclasses.dataclass
class TimeOfFlightRange(CBor2Message):
    range: float
