import time
from abc import ABC, abstractmethod
from typing import Any

from dtps import DTPSContext
from dtps_http import RawData
from duckietown_messages.standard.dictionary import Dictionary
from duckietown_messages.standard.header import Header


class AbstractHardwareTest(ABC):
    _node: Any
    _test_out_queue: DTPSContext

    def __init__(self, node: Any, test_out_queue: DTPSContext) -> None:
        self._node = node
        self._test_out_queue = test_out_queue
        self.message = ""

    @abstractmethod
    async def run_test(self, dictionary: Dictionary) -> None:
        """Run the test."""
        pass

    async def on_run_test(self, raw_data: RawData) -> None:
        dictionary: Dictionary = Dictionary.from_rawdata(raw_data)
        test_id = dictionary.data["test_id"]
        self._node.loginfo(f"[{test_id}] Running test...")
        try:
            await self.run_test(dictionary)
            success = True
        except Exception as error:
            self._node.logerr(f"Error running test: {error}")
            success = False
        data = {
            "success": success,
            "lst_blocks": [
                {
                    "key": "Test parameters",
                    "type": "string",
                    "value": self.message,
                }
            ]
        }
        timestamp = time.time()
        header = Header(timestamp=timestamp)
        dictionary = Dictionary(header=header, data=data)
        raw_data = dictionary.to_rawdata()
        await self._test_out_queue.publish(raw_data)
        self._node.loginfo(f"[{test_id}] Test result sent...")
