import asyncio
from typing import Union
from dt_node_utils.constants import NodeType
from dt_node_utils.node import Node
from dtps.ergo_ui import DTPSContext
from dtps_http.object_queue import TransformError
from dtps_http.structures import RawData
from dtps import context

BASE_URL = "http://localhost:2120/"

class RPCListenerTest(Node):
    def __init__(self, no_switchboard = True):
        super().__init__(name="rpc-listener", kind=NodeType.DEBUG, description="RPC Listener Tester")
        self.no_switchboard = no_switchboard

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
        if self.no_switchboard:
            self.loginfo("Using direct call to url " + BASE_URL)
            self.loginfo("Creating queue")

            me = await context("self", environment={"DTPS_BASE_SELF" : f"create:{BASE_URL}"})
            queue : DTPSContext = await (me / "call_me").queue_create(transform=self._transform)
        else:
            self.loginfo("Using switchboard")
            await self.dtps_init()
            queue = await (self.context / "in" / "call_me").queue_create(transform=self._transform)
            await (self.switchboard / "call_me").expose(queue)

        self.loginfo("Waiting for RPC call...")
        while True:
            await asyncio.sleep(1)
        
if __name__ == "__main__":
    # Parse the command line argument --use-switchboard
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-switchboard", action="store_true", help="Use the switchboard", default=False)
    args = parser.parse_args()
    
    # initialize the node
    node = RPCListenerTest(no_switchboard=args.no_switchboard)
    # keep the node alive
    node.spin()
        