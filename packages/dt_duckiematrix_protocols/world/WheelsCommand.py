from typing import Dict

import dataclasses

from dt_duckiematrix_protocols.world import CBor2Message


@dataclasses.dataclass
class WheelsCommand(CBor2Message):
    wheels: Dict[str, float]
