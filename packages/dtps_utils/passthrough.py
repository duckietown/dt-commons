import logging
from typing import Optional, List, Dict, Callable

from dtps import DTPSContext, PublisherInterface, SubscriptionInterface, context
from dtps_http import RawData
from duckietown_messages.network.dtps.context import DTPSContextMsg

from duckietown_messages.utils.exceptions import DataDecodingError

logger = logging.getLogger("dtps-passthrough")
logger.setLevel(logging.INFO)

SubPath = str


class DTPSPassthrough:
    __counter: int = 0

    def __init__(
            self,
            base: DTPSContext,
            src: Optional[DTPSContext],
            dst: Optional[DTPSContext],
            subpaths: List[SubPath],
            src_path: List[str] = None,
            dst_path: List[str] = None,
            transformations: Optional[Dict[SubPath, Callable[[RawData], RawData]]] = None
            ):
        self._base: DTPSContext = base
        self._src: Optional[DTPSContext] = src
        self._dst: Optional[DTPSContext] = dst
        self._subpaths: List[SubPath] = subpaths
        # transformations to apply to the data before republishing
        self._transformations: Optional[Dict[SubPath, Callable[[RawData], RawData]]] = transformations
        # the descriptors of the current source and destination
        self._current_src: Optional[DTPSContextMsg] = None
        self._current_dst: Optional[DTPSContextMsg] = None
        # the DTPS queues where the source and destination configurations are published and subscribed
        self._src_q: Optional[DTPSContext] = None
        self._dst_q: Optional[DTPSContext] = None
        # the paths to the source and destination contexts
        self._src_path: List[str] = src_path or []
        self._dst_path: List[str] = dst_path or []
        # internal state
        self._initialized: bool = False
        self._subscribers: Optional[Dict[SubPath, SubscriptionInterface]] = None
        self._publishers: Optional[Dict[SubPath, PublisherInterface]] = None

    @property
    def is_active(self) -> bool:
        return self._subscribers is not None and self._publishers is not None

    async def set_source(self, cxt: Optional[DTPSContext], path: List[str]):
        await self._clear_subscribers()
        self._src = cxt
        self._src_path = path
        self._current_src = await self._cxt_descriptor("src", cxt, path)
        await self._src_q.publish(self._msg_to_rawdata(self._current_src))
        await self.astart()

    async def set_destination(self, cxt: Optional[DTPSContext], path: List[str]):
        await self._clear_publishers()
        self._dst = cxt
        self._dst_path = path
        self._current_dst = await self._cxt_descriptor("dst", cxt, path)
        await self._dst_q.publish(self._msg_to_rawdata(self._current_dst))
        await self.astart()

    async def _clear_subscribers(self):
        if self._subscribers:
            for subpath, sub in self._subscribers.items():
                logger.info(f"Clearing subscriber for path '{subpath}'...")
                try:
                    await sub.unsubscribe()
                except Exception as e:
                    logger.warning(f"Could not unsubscribe from subpath '{subpath}': {e}")
        self._subscribers = None

    async def _clear_publishers(self):
        if self._publishers:
            for subpath, pub in self._publishers.items():
                logger.info(f"Clearing publisher for path '{subpath}'...")
                try:
                    await pub.terminate()
                except Exception as e:
                    logger.warning(f"Could not terminate publisher for subpath '{subpath}': {e}")
        self._publishers = None

    async def _ainit(self):
        logger.info("Configuring passthrough...")
        # create connection configuration context
        cxt = self._base.navigate(f"passthrough-{DTPSPassthrough.__counter}")
        # create source and destination queues
        self._src_q = await cxt.navigate("source").queue_create()
        self._dst_q = await cxt.navigate("destination").queue_create()
        # add fake initial values
        self._current_src = await self._cxt_descriptor("src", self._src, self._src_path)
        self._current_dst = await self._cxt_descriptor("dst", self._dst, self._dst_path)
        await self._src_q.publish(self._msg_to_rawdata(self._current_src))
        await self._dst_q.publish(self._msg_to_rawdata(self._current_dst))
        # when a new configuration is pushed into the queue, we will update the connection

        async def _on_new_source(rd: RawData):
            if not self._initialized:
                return
            # ---
            try:
                new_src: Optional[DTPSContextMsg] = DTPSContextMsg.from_rawdata(rd, allow_none=True)
            except DataDecodingError as e:
                logger.error(f"Could not decode passthrough source configuration: {e.message}")
                return
            if new_src == self._current_src:
                return
            if new_src is None:
                if self._src is not None:
                    await self.set_source(None, [])
                return
            # create new source context
            cxt_args: dict = {
                "base_name": new_src.name,
            }
            # add optional URLs
            if new_src.urls:
                cxt_args["urls"] = new_src.urls
            # create context
            src = await context(**cxt_args)
            # navigate to optional path
            if new_src.path:
                src = src.navigate(new_src.path)
            # set source
            logger.info(f"Source context set to: {new_src}")
            await self.set_source(src, [])

        async def _on_new_destination(rd: RawData):
            if not self._initialized:
                return
            # ---
            try:
                new_dst: Optional[DTPSContextMsg] = DTPSContextMsg.from_rawdata(rd, allow_none=True)
            except DataDecodingError as e:
                logger.error(f"Could not decode passthrough destination configuration: {e.message}")
                return
            if new_dst == self._current_dst:
                return
            if new_dst is None:
                if self._dst is not None:
                    await self.set_destination(None, [])
                return
            # create new destination context
            cxt_args: dict = {
                "base_name": new_dst.name,
            }
            # add optional URLs
            if new_dst.urls:
                cxt_args["urls"] = new_dst.urls
            # create context
            dst = await context(**cxt_args)
            # navigate to optional path
            if new_dst.path:
                dst = dst.navigate(new_dst.path)
            # set destination
            logger.info(f"Destination context set to {new_dst}")
            await self.set_destination(dst, [])

        await self._src_q.subscribe(_on_new_source)
        await self._dst_q.subscribe(_on_new_destination)
        DTPSPassthrough.__counter += 1

        # mark it as initialized
        self._initialized = True
        logger.info("Passthrough configured.")

    async def astart(self):
        if not self._initialized:
            await self._ainit()
            logger.info("Starting passthrough...")
        else:
            logger.info("Restarting passthrough...")
        # check source
        if self._src is None:
            logger.info("No source to subscribe to. Remaining idle.")
            return
        # check destination
        if self._dst is None:
            logger.info("No destination to publish to. Remaining idle.")
            return
        # create publishers if needed
        dst1: DTPSContext = self._dst.navigate(*self._dst_path)
        if self._publishers is None:
            # create continuous publishers
            self._publishers = {
                p: (await dst1.navigate(p).publisher()) for p in self._subpaths
            }

        # create subscribers if needed
        src1: DTPSContext = self._src.navigate(*self._src_path)
        if self._subscribers is None:
            self._subscribers = {}
            for p in self._subpaths:
                async def _republish(rd: RawData):
                    rd_transformed: RawData = rd
                    if self._transformations and p in self._transformations:
                        rd_transformed = self._transformations[p](rd)
                        if rd_transformed is None:
                            raise RuntimeError(f"Transformation function for path '{p}' returned 'None'")
                    await self._publishers[p].publish(rd_transformed)

                self._subscribers[p] = (await src1.navigate(p).subscribe(_republish))

        base: str = "/".join(src1.get_path_components())
        logger.info("Passthrough started on the following paths:" +
                    f"\n\t - {base}/".join([""] + self._subpaths) + "\n")

    @staticmethod
    async def _cxt_descriptor(_name: str, _cxt: Optional[DTPSContext], path: List[str]) -> Optional[DTPSContextMsg]:
        msg: Optional[DTPSContextMsg] = None
        if _cxt is not None:
            msg = DTPSContextMsg(
                name=_name,
                urls=await _cxt.get_urls(),
                path="/".join(path)
            )
        return msg

    @staticmethod
    def _msg_to_rawdata(msg: Optional[DTPSContextMsg]) -> RawData:
        if msg is None:
            return RawData.json_from_native_object(None)
        return msg.to_rawdata()

    def stop(self):
        pass
