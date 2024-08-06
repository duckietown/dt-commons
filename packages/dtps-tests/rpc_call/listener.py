import asyncio
from typing import Union
from dt_node_utils.constants import NodeType
from dt_node_utils.node import Node
from dtps_http.object_queue import TransformError
from dtps_http.structures import RawData


class RPCListenerTest(Node):
    def __init__(self):
        super().__init__(name="rpc-listener-tester", kind=NodeType.DEBUG, description="RPC Listener Tester")

    async def _transform(self, data : RawData) -> Union[RawData, TransformError]:
        self.loginfo("Received an RPC call")
        
        try:
            content = data.get_as_native_object()
            self.loginfo(f"Received data: {content}")
            self.loginfo("Sending response")
        
            return RawData.simple_string("Hello, you!")
        
        except Exception as e:
            self.logerr(f"Error: {e}")
            return TransformError(f"Failed to process data. Error: {e}")
        
        
    async def worker(self):
        await self.dtps_init()
        queue = await (self.context / "in" / "call_me").queue_create(transform=self._transform)
        await (self.switchboard / "call_me").expose(queue)
        
        self.loginfo("Waiting for RPC call...")
        while True:
            await asyncio.sleep(1)
        
if __name__ == "__main__":
    # initialize the node
    node = RPCListenerTest()
    # keep the node alive
    node.spin()
        