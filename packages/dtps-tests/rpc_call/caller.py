import asyncio
from dt_node_utils.constants import NodeType
from dt_node_utils.node import Node
from dtps.ergo_ui import DTPSContext
from dtps_http.structures import RawData


class RPCCallerTest(Node):
    def __init__(self):
        super().__init__(name="rpc-tester", kind=NodeType.DEBUG, description="RPC Call Tester")

        
    async def worker(self):
        await self.dtps_init()
        queue = await (self.switchboard / "call_me").until_ready()

        while True:
            await self.call_rpc(queue)
            await asyncio.sleep(1)
        
    async def call_rpc(self, queue : DTPSContext):
        try:
            self.loginfo("Calling RPC")
            response = await queue.call(RawData.simple_string("Hello, World!"))
            self.loginfo(f"Received response: {response}")
        except Exception as e:
            self.logerr(f"Error: {e}")
            
if __name__ == "__main__":
    # initialize the node
    node = RPCCallerTest()
    # keep the node alive
    node.spin()