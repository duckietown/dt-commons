import asyncio
import logging
import traceback
from typing import Callable, Awaitable


def create_task(f: Callable[[], Awaitable], name: str, logger: logging.Logger = None):
    async def coro():
        try:
            await f()
        except asyncio.CancelledError:
            raise
        except Exception:
            msg = f"Uncaught exception in {name} method:\n\n{traceback.format_exc()}\n"
            if logger:
                logger.error(msg)
            else:
                print(msg)
            raise

    return asyncio.create_task(coro())
