import asyncio
import traceback
from typing import Callable, Type, Optional, Union, Coroutine, TypeVar

from dtps import DTPSContext
from dtps_http import RawData
from duckietown_messages.base import BaseMessage
from duckietown_messages.utils.exceptions import DataDecodingError


T = TypeVar('T', bound=BaseMessage)


class DTPSSubscriber:

    def __init__(self,
                 cxt: DTPSContext,
                 callback: Union[Callable[[RawData], Coroutine], Callable[[T], Coroutine]],
                 decoder: Type[BaseMessage] = None,
                 max_frequency: Optional[float] = None,
                 queue_size: int = 1,
                 forget_old_messages: bool = True,):
        self._cxt: DTPSContext = cxt
        self._callback: Union[Callable[[RawData], Coroutine], Callable[[T], Coroutine]] = callback
        self._decoder: Optional[Type[BaseMessage]] = decoder
        self._max_frequency: Optional[float] = max_frequency
        self._queue_size: int = queue_size
        self._forget_old_messages: bool = forget_old_messages
        # internal state
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._sub = None

    async def init(self):
        # subscribe
        self._sub = await self._cxt.subscribe(self._cb, max_frequency=self._max_frequency)
        # create processor task
        await asyncio.create_task(self._processor())

    async def _processor(self):
        while True:
            data: RawData = await self._queue.get()

            # noinspection PyBroadException
            try:
                # ==> this block runs user code, we need to catch exceptions
                if self._decoder:
                    try:
                        msg = self._decoder.from_rawdata(data)
                    except DataDecodingError as e:
                        print(f"ERROR: Failed to decode an incoming message on queue {self._cxt}: {e.message}")
                        continue
                    await self._callback(msg)
                else:
                    await self._callback(data)
                # <== this block runs user code, we need to catch exceptions
            except Exception:
                print(f"Exception in DTPSSubscriber callback for queue {self._cxt}:")
                traceback.print_exc()

    async def _cb(self, data: RawData):
        try:
            self._queue.put_nowait(data)
            print(data)
        except asyncio.QueueFull:
            if self._forget_old_messages:
                try:
                    await self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                self._queue.put_nowait(data)
                print(data)
