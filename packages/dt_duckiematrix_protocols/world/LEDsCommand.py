from typing import Dict

import dataclasses

from dt_duckiematrix_protocols.world import CBor2Message


@dataclasses.dataclass
class LEDCommand:
    color: str
    intensity: float


@dataclasses.dataclass
class LEDsCommand(CBor2Message):
    leds: Dict[str, LEDCommand]

    def as_dict(self) -> dict:
        return {
            led_key: led.__dict__ for led_key, led in self.leds.items()
        }
