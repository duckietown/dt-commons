import logging
from typing import Optional, List, Dict, Callable

from dtps import DTPSContext, PublisherInterface, SubscriptionInterface, context
from dtps_http import RawData

from duckietown_messages.network.dtps.passthrough_connection import DTPSPassthroughConnection
from duckietown_messages.utils.exceptions import DataDecodingError

logger = logging.getLogger("dtps-passthrough")
logger.setLevel(logging.INFO)

SubPath = str


class DTPSPassthrough:
    __counter: int = 0

    def __init__(self, base: DTPSContext, src: Optional[DTPSContext], dst: DTPSContext, paths: List[SubPath],
                 transformations: Optional[Dict[SubPath, Callable[[RawData], RawData]]] = None):
        self._base: DTPSContext = base
        self._src: Optional[DTPSContext] = src
        self._dst: DTPSContext = dst
        self._paths: List[SubPath] = paths
        self._transformations: Optional[Dict[SubPath, Callable[[RawData], RawData]]] = transformations
        # ---
        self._connection: Optional[DTPSContext] = None
        self._initialized: bool = False
        # ---
        self._subscriptions: Optional[Dict[SubPath, SubscriptionInterface]] = None
        self._publishers: Optional[Dict[SubPath, PublisherInterface]] = None

    @property
    def is_active(self) -> bool:
        return self._subscriptions is not None

    async def set_source(self, src: Optional[DTPSContext]):
        await self.stop()
        self._src = src
        await self.astart()

    async def _ainit(self):
        logger.info("Configuring passthrough...")
        # create connection configuration context
        self._connection = await self._base.navigate(f"passthrough-{DTPSPassthrough.__counter}").queue_create()
        # add fake initial value
        await self._connection.publish(RawData.json_from_native_object(None))
        # when a new configuration is pushed into the queue, we will update the connection

        async def _set_source(rd: RawData):
            if not self._initialized:
                return
            # ---
            try:
                passthrough: Optional[DTPSPassthroughConnection] = (
                    DTPSPassthroughConnection.from_rawdata(rd, allow_none=True))
            except DataDecodingError as e:
                logger.error(f"Could not decode passthrough configuration: {e.message}")
                return
            if passthrough is None:
                if self._src is not None:
                    await self.set_source(None)
                return
            # create new source context
            cxt_args: dict = {
                "base_name": passthrough.source.name,
            }
            # add optional URLs
            if passthrough.source.urls:
                cxt_args["urls"] = passthrough.source.urls
            # create context
            src = await context(**cxt_args)
            # navigate to optional path
            if passthrough.source.path:
                src = src.navigate(passthrough.source.path)
            # set paths
            if passthrough.paths:
                self._paths = passthrough.paths
            # set source
            logger.info(f"Source context set to {passthrough.source}")
            await self.set_source(src)

        await self._connection.subscribe(_set_source)
        DTPSPassthrough.__counter += 1
        # create continuous publishers
        if self._publishers is None:
            self._publishers = {
                p: (await self._dst.navigate(p).publisher()) for p in self._paths
            }

        # mark it as initialized
        self._initialized = True
        logger.info("Passthrough configured.")

    async def astart(self):
        if not self._initialized:
            await self._ainit()
        logger.info("Starting passthrough...")
        # check source
        if self._src is None:
            logger.info("Started but with no source to subscribe to. Remaining idle.")
            return
        # create subscriptions
        self._subscriptions = {}
        for p in self._paths:
            async def _republish(rd: RawData):
                rd_transformed: RawData = rd
                if self._transformations and p in self._transformations:
                    rd_transformed = self._transformations[p](rd)
                    if rd_transformed is None:
                        raise RuntimeError(f"Transformation function for path '{p}' returned None")
                await self._publishers[p].publish(rd_transformed)

            self._subscriptions[p] = (await self._src.navigate(p).subscribe(_republish))

        base: str = "/".join(self._src.get_path_components())
        logger.info("Passthrough started on the following paths:" +
                    f"\n\t - {base}/".join([""] + self._paths) + "\n")

    async def stop(self):
        if self._subscriptions:
            logger.info("Stopping passthrough...")
            for subpath, sub in self._subscriptions.items():
                try:
                    await sub.unsubscribe()
                except Exception as e:
                    logger.warning(f"Could not unsubscribe from subpath '{subpath}': {e}")
        self._subscriptions = None
        self._src = None
        logger.info("Passthrough stopped.")
