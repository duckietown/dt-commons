import asyncio
from dt_node_utils.constants import NodeType
from dt_node_utils.node import Node
from dtps.ergo_ui import DTPSContext
from dtps_http.structures import RawData
from dtps import context

BASE_URL = "http://localhost:2120/"

class RPCCallerTest(Node):
    def __init__(self, no_switchboard = True):
        super().__init__(name="rpc-caller", kind=NodeType.DEBUG, description="RPC Call Tester")
        self.no_switchboard = no_switchboard
        
    async def worker(self):
        if self.no_switchboard:
            self.loginfo("Using direct call to url " + BASE_URL)
            dtps_context = await context("self", environment={"DTPS_BASE_SELF":"http://localhost:2120/"})

        else:
            self.loginfo("Using switchboard")
            await self.dtps_init()
            dtps_context = await (self.switchboard).until_ready()

        queue : DTPSContext = await (dtps_context / "call_me").until_ready()

        while True:
            await self.call_rpc(queue)
            await asyncio.sleep(1)
        
    async def call_rpc(self, queue : DTPSContext):
        try:
            self.loginfo(f"Calling the queue {queue}")
            response = await queue.call(RawData.simple_string("Hello, World!"))
            self.loginfo(f"Received response: {response}")
        except Exception as e:
            self.logerr(f"Error: {e}")
            
if __name__ == "__main__":
    # Parse the command line argument --use-switchboard
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-switchboard", action="store_true", help="Use the switchboard", default=False)
    args = parser.parse_args()
    
    # initialize the node
    node = RPCCallerTest(no_switchboard=args.no_switchboard)
    # keep the node alive
    node.spin()