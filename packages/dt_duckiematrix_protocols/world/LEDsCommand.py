from typing import Dict

import dataclasses

from cbor2 import loads

from dt_duckiematrix_protocols import CBorMessage


@dataclasses.dataclass
class LEDCommand:
    color: str
    intensity: float


@dataclasses.dataclass
class LEDsCommand(CBorMessage):
    leds: Dict[str, LEDCommand]

    def as_dict(self) -> dict:
        return {
            "leds": {led_key: led.__dict__ for led_key, led in self.leds.items()}
        }

    @classmethod
    def from_bytes(cls, data: bytes) -> 'LEDsCommand':
        d = loads(data)
        return LEDsCommand(
            leds={
                str(i): LEDCommand(**l) for i, l in d['leds'].items()
            }
        )
