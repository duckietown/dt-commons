from typing import Dict

import dataclasses

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class WheelsCommand(CBorMessage):
    wheels: Dict[str, float]
