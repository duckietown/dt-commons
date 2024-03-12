import asyncio
import inspect
import os
import traceback
from abc import abstractmethod
from typing import Optional, Awaitable, Callable, Any, List, Coroutine, Tuple

from dt_class_utils import DTProcess
from dt_robot_utils import get_robot_name
from dtps import DTPSContext, context
from .asyncio import create_task
from .config import NodeConfiguration
from .constants import NodeHealth, NodeType
from .dtps import default_context_env
from .package import Package
from .profiler import CodeProfiler

FSM_NODE_CONTROL: bool = os.environ.get("FSM_NODE_CONTROL", "0").lower() in ["1", "y", "yes"]


class Node(DTProcess):
    """
    Parent class for all Duckietown nodes.

    Args:
       name (:obj:`str`): a unique, descriptive name for the node
       kind (:py:class:`dt_node_utils.NodeType`): a node type
       description (:obj: `str`): a node description
       ghost (:obj: `bool`): excludes the node from the diagnostics

    Properties:
        kind (:py:class:`dt_node_utils.NodeType`): the node type
        description (:obj:`str`): the description of the node
        is_ghost:   (:obj:`bool`): (Internal use only) whether the node is a ghost
        switch:     (:obj:`bool`): current state of the switch (`true=ON`, `false=OFF`)
        parameters: (:obj:`list`): list of parameters defined within the node
        subscribers: (:obj:`list`): list of subscribers defined within the node
        publishers: (:obj:`list`): list of publishers defined within the node

    Service:
        ~switch:
            Switches the node between active state and inactive state.

            input:
                data (`bool`): The desired state. ``True`` for active, ``False`` for inactive.

            outputs:
                success (`bool`): ``True`` if the call succeeded
                message (`str`): Used to give details about success

    """

    def __init__(
            self,
            name: str,
            kind: NodeType,
            description: str = None,
            ghost: bool = False,
            fsm_controlled: bool = False
    ):
        super().__init__(name=name, catch_signals=False)
        self._description: Optional[str] = description
        self._kind: NodeType = kind
        self._ghost: bool = ghost
        self._health: NodeHealth = NodeHealth.STARTING
        self._health_reason: Optional[str] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        self.loginfo("Initializing...")

        # robot name
        self._robot_name: str = get_robot_name()

        # find package
        node_fpath: str = os.path.realpath(inspect.getfile(self.__class__))
        self._package: Optional[Package] = Package.nearest(node_fpath)

        # Handle publishers, subscribers, and the state switch
        self._switch: bool = False if (fsm_controlled and FSM_NODE_CONTROL) else True
        self.loginfo(f"Node starting with switch={self._switch}")
        self.logdebug(f"Switch configuration: "
                      f"fsm_controlled:{fsm_controlled}, env[FSM_NODE_CONTROL]:{FSM_NODE_CONTROL}")

        # create switch service for node
        # TODO

        # register node against the diagnostics manager
        # TODO

        # provide a public interface to the context manager to use as `with self.profiler("PHASE")`
        self.profiler = CodeProfiler()

        # DTPS contexts
        self.context: Optional[DTPSContext] = None
        self.switchboard: Optional[DTPSContext] = None

        # events
        self.switchboard_ready = asyncio.Event()

        # if enable_dtps:
        #     # create self context
        #     coro: Coroutine = context("self", default_context_env("self"))
        #     self.context = consume(DTPSContext, coro)
        #     # expose on switchboard
        #     coro: Coroutine = context("switchboard")
        #     self.switchboard = consume(DTPSContext, coro)
        #     self.switchboard.navigate(f"node/{self.name}").expose(self.context)

        # mark node as healthy and STARTED
        self.set_health(NodeHealth.STARTED)

    # Read-only properties for the private attributes
    @property
    def is_ghost(self) -> bool:
        """Whether this is a ghost node (diagnostics will skip it)"""
        return self._ghost

    @property
    def kind(self) -> NodeType:
        return self._kind

    @property
    def description(self) -> Optional[str]:
        return self._description

    # Read-only properties for the private attributes
    @property
    def switch(self) -> bool:
        """Current state of the node on/off switch"""
        return self._switch

    @property
    def package(self) -> Optional[Package]:
        return self._package

    def set_health(self, health, reason=None):
        if not isinstance(health, NodeHealth):
            raise ValueError(
                "Argument 'health' must be of type duckietown.NodeHealth. "
                "Got %s instead" % str(type(health))
            )
        self.loginfo("Health status changed [%s] -> [%s]" % (self._health.name, health.name))
        self._health = health
        self._health_reason = None if reason is None else str(reason)
        # update node health in the diagnostics manager
        # TODO

    async def dtps_init(self, config: Optional[NodeConfiguration] = None):
        # create self context
        self.context = await context("self", default_context_env("self", self.name))
        # create switchboard context
        self.switchboard = (await context("switchboard")).navigate(self._robot_name)
        self.switchboard_ready.set()
        # post node config
        if config is not None:
            await config.expose(self.context / "config")

    async def dtps_expose(self):
        await (self.switchboard / "nodes" / self.name).expose(self.context)

    @abstractmethod
    async def worker(self):
        raise NotImplementedError("Method 'worker' must be implemented by the final node class.")

    async def _worker(self):
        await self.worker()

    async def __spin(self):
        self._event_loop = asyncio.get_event_loop()

        try:
            await asyncio.wait([
                create_task(self._worker, "worker", self.logger),
                *[
                    create_task(sidecar, f"sidecar[{name}]", self.logger) for name, sidecar in self._get_sidecars()
                ]
            ])
        except asyncio.CancelledError:
            self.loginfo("Initiated shutdown sequence")
            self.__on_shutdown()
            self.loginfo("Shutdown sequence completed")

    def _get_sidecars(self) -> List[Tuple[str, Callable[[], Awaitable]]]:
        return [
            (name, method)
            for name, method in
            inspect.getmembers(self, predicate=inspect.ismethod)
            if getattr(method, "__sidecar__", False)
        ]

    def spin(self):
        try:
            asyncio.run(self.__spin())
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.__on_shutdown()

    async def join(self):
        while not self.is_shutdown:
            await asyncio.sleep(0.5)

    def call_soon(self, coro: Callable[[Any], Awaitable[None]], *args, **kwargs):
        if self._event_loop is None:
            raise RuntimeError("Event loop is not initialized yet. Call spin() first.")

        async def _coro():
            await coro(*args, **kwargs)

        asyncio.run_coroutine_threadsafe(_coro(), self._event_loop)

    def loginfo(self, msg):
        self.logger.info(msg)

    def logdebug(self, msg):
        self.logger.debug(msg)

    def logwarn(self, msg):
        self.set_health(NodeHealth.WARNING, msg)
        self.logger.warning(msg)

    def logerr(self, msg):
        self.set_health(NodeHealth.ERROR, msg)
        self.logger.error(msg)

    def logfatal(self, msg):
        self.set_health(NodeHealth.FATAL, msg)
        self.logger.fatal(msg)

    def on_switch_on(self):
        pass

    def on_switch_off(self):
        pass

    # def _srv_switch(self, request):
    #     """
    #     Args:
    #         request (:obj:`std_srvs.srv.SetBool`): The switch request from the ``~switch`` callback
    #
    #     Returns:
    #         :obj:`std_srvs.srv.SetBoolResponse`: Response for successful feedback
    #
    #     """
    #     old_state = self._switch
    #     self._switch = new_state = request.data
    #     # propagate switch change to publishers and subscribers
    #     for pub in self.publishers:
    #         pub.active = self._switch
    #     for sub in self.subscribers:
    #         sub.active = self._switch
    #     # tell the node about the switch
    #     on_switch_fcn = {False: self.on_switch_off, True: self.on_switch_on}[self._switch]
    #     on_switch_fcn()
    #     # update node switch in the diagnostics manager
    #     if DTROSDiagnostics.enabled():
    #         DTROSDiagnostics.getInstance().update_node(enabled=self._switch)
    #     # create a response to the service call
    #     msg = "Node switched from [%s] to [%s]" % ("on" if old_state else "off", "on" if new_state else "off")
    #     # print out the change in state
    #     self.log(msg)
    #     # reply to the service call
    #     response = SetBoolResponse()
    #     response.success = True
    #     response.message = msg
    #     return response

    def __on_shutdown(self):
        self.on_shutdown()

    def on_shutdown(self):
        # this function does not do anything, it is called when the node shuts down.
        # It can be redefined by the user in the final node class.
        pass


