import logging
import os
from typing import TypeVar, Type, Union, Any, Callable, Coroutine, Optional, Dict

import cbor2

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
CBORSerializable = Union[dict, list, str, int, float, bool, None]


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

    async def declare(self,
                      key: str,
                      *,
                      value: Union[BaseMessage, dict, list, str, int, float, bool, bytes, None] = NOTSET,
                      default: Union[BaseMessage, dict, list, str, int, float, bool, bytes, None] = NOTSET,
                      persist: bool = False):
        await self._ensure_inited()
        # ---
        # base messages can be turned into dicts
        if isinstance(value, BaseMessage):
            value = value.dict()
        # ---
        queue_exists: bool = await self.exists(key)
        if queue_exists:
            return
        # create remote queue
        cxt: DTPSContext
        # queue metadata
        app_data: Dict[str, CBORSerializable] = {
            "kvstore.persist": persist,
        }
        # add initial value
        if value is not NOTSET:
            app_data["kvstore.initial"] = value
        # add default value
        if default is not NOTSET:
            app_data["kvstore.default"] = default
        # serialize the app data
        app_data_bin: Dict[str, bytes] = {k: cbor2.dumps(v) for k, v in app_data.items()}
        # create remote queue
        await self._data.navigate(key).queue_create(app_data=app_data_bin)

    async def set(self, key: str, value: Union[BaseMessage, dict, list, str, int, float, bool, bytes, None]):
        await self._ensure_inited()
        # ---
        # base messages can be turned into dicts
        if isinstance(value, BaseMessage):
            value = value.dict()
        # ---
        queue_exists: bool = await self.exists(key)
        if not queue_exists:
            raise KeyError(f"Key '{key}' not found. Use KVStore.declare() to create it first.")
        cxt: DTPSContext = self._data.navigate(key)
        # publish to queue
        await cxt.publish(RawData.json_from_native_object(value))

    async def subscribe(self, key: str, cb: Callable[[RawData], Coroutine[Any, Any, None]]):
        await self._ensure_inited()
        # ---
        # make sure the key exists
        queue_exists: bool = await self.exists(key)
        if not queue_exists:
            msg = f"Key '{key}' not found. Use KVStore.set() to create it first."
            raise KeyError(msg)
        # subscribe to the queue
        cxt = self._data.navigate(key)
        await cxt.subscribe(cb)
