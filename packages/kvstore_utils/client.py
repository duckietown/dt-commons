import logging
import os
from typing import TypeVar, Type, Union, Any, Callable, Coroutine, Optional

from dt_robot_utils import get_robot_name
from dtps import context, DTPSContext
from dtps_http import RawData
from duckietown_messages.base import BaseMessage

# create logger
logging.basicConfig()
logger = logging.getLogger("kvstore-utils")
logger.setLevel(logging.INFO)
if 'DEBUG' in os.environ and os.environ['DEBUG'].lower() in ['true', 'yes', '1']:
    logger.setLevel(logging.DEBUG)

T = TypeVar("T")
NOTSET = object()


class NoValue(KeyError):
    pass


class KVStore:

    def __init__(self):
        self._robot: str = get_robot_name()
        self._cxt: Optional[DTPSContext] = None
        self._data: Optional[DTPSContext] = None

    async def init(self):
        self._cxt = await context("kvstore")
        self._data = self._cxt.navigate("data")

    async def _ensure_inited(self):
        if self._cxt is None:
            await self.init()

    async def has(self, key: str) -> bool:
        await self._ensure_inited()
        # ---
        cxt = self._data.navigate(key)
        await cxt.data_get()
        rd: RawData = await cxt.data_get()
        if rd.content_type == "text/plain" and rd.content == b"":
            return False
        return True

    async def exists(self, key: str) -> bool:
        await self._ensure_inited()
        # ---
        cxt = self._data.navigate(key)
        return await cxt.exists()

    async def get(self, cls: Type[T], key: str, default: Any = NOTSET) -> T:
        await self._ensure_inited()
        # ---
        cxt = self._data.navigate(key)
        rd: RawData = await cxt.data_get()
        if rd.content_type == "text/plain" and rd.content == b"":
            if default is NOTSET:
                msg = f"Key '{key}' has no value set"
                raise NoValue(msg)
            return default
        # decode the response
        native: object = rd.get_as_native_object()
        if not isinstance(native, cls):
            msg = f"Expected value of type '{cls}' but got '{native.__class__.__name__}' instead"
            raise ValueError(msg)
        return native

    async def set(self, key: str, value: Union[BaseMessage, dict, list, str, int, float, bool, bytes],
                  persist: bool = False):
        await self._ensure_inited()
        # ---
        # base messages can be turned into dicts
        if isinstance(value, BaseMessage):
            value = value.dict()
        # ---
        queue_exists: bool = await self.exists(key)
        cxt: DTPSContext
        if not queue_exists:
            # create remote queue
            cxt = await self._data.navigate(key).queue_create(
                app_data={
                    "kvstore.persist": persist,
                    "kvstore.initial": value,
                },
            )
            # TODO: DTSW-5915: Given that the metadata does not reach the queue creation, we need to set the value
            # TODO: to be removed once DTSW-5915 is resolved
            await cxt.publish(RawData.json_from_native_object(value))
        else:
            cxt = self._data.navigate(key)
            # publish to queue
            await cxt.publish(RawData.json_from_native_object(value))

    async def on_update(self, key: str, cb: Callable[[Any], Coroutine[Any, Any, None]],
                        create_if_missing: bool = False, initial_value: Any = NOTSET):
        await self._ensure_inited()
        # ---
        if create_if_missing and initial_value is NOTSET:
            raise ValueError("If create_if_missing is True, initial_value must be provided")
        # check if the key exists
        queue_exists: bool = await self.exists(key)
        if not queue_exists:
            if not create_if_missing:
                msg = f"Key '{key}' not found. Use create_if_missing=True to create it"
                raise KeyError(msg)
            # create remote queue
            await self.set(key, initial_value)
        # subscribe to the queue
        cxt = self._data.navigate(key)
        await cxt.subscribe(cb)
