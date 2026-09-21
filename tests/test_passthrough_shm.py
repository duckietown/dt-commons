"""Functional tests for DTPSPassthrough's shared-memory publish transport.

These cover the ``publish_transports`` option of :class:`DTPSPassthrough`, which
lets a relayed subpath be republished over a shared-memory channel instead of
(or in addition to) the regular HTTP/WebSocket path::

    transport = self._publish_transports.get(subpath)
    if transport is None:
        await publisher.publish(rd)
    else:
        await publisher.publish(rd, shm_path=transport.shm_path, shm_only=transport.shm_only)

Two cases are exercised:

* ``control``  - no ``publish_transports``. Data must reach an ordinary
  subscriber and no SHM channel may be created.
* ``shm_only`` - a transport with ``shm_only=True``. Data must round-trip
  through the SHM channel (payload *and* content-type preserved), and must
  NOT be delivered over the ordinary HTTP path.

The second assertion matters: a SHM write failure silently falls back to HTTP,
so a test that only checked "data arrived" would pass even when SHM never ran.

Run inside a dt-commons container (needs ``dtps``/``dtps_utils`` on the path)::

    source /environment.sh && python3 tests/test_passthrough_shm.py
"""

import asyncio
import glob
import os
import shutil
import tempfile
from typing import Dict, List, Optional
from urllib.parse import quote

from dtps import context
from dtps.shm import create_shm_subscription
from dtps_http import RawData
from dtps_utils.passthrough import DTPSPassthrough, PassthroughPublisherTransport

SUBPATH: str = "jpeg"
PAYLOAD: bytes = b"CAMERA-FRAME-PAYLOAD-0123456789"
CONTENT_TYPE: str = "image/jpeg"
RECEIVE_TIMEOUT: float = 8.0
# how long we wait before concluding that nothing arrived over HTTP
NEGATIVE_TIMEOUT: float = 3.0


async def _make_passthrough(
    workdir: str,
    transports: Optional[Dict[str, PassthroughPublisherTransport]],
):
    """Build a source -> destination passthrough inside a single DTPS node."""
    sock: str = quote(os.path.join(workdir, "node.sock"), safe="")
    base = await context("base", urls=[f"create:http+unix://{sock}/"])
    source = await base.navigate("src").navigate(SUBPATH).queue_create()
    await base.navigate("dst").navigate(SUBPATH).queue_create()

    passthrough = DTPSPassthrough(
        base=base,
        src=base,
        dst=base,
        subpaths=[SUBPATH],
        src_path=["src"],
        dst_path=["dst"],
        publish_transports=transports,
    )
    await passthrough.astart()
    assert passthrough.is_active, "passthrough failed to activate"
    return base, source


def _shm_artifacts(shm_dir: str) -> List[str]:
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(shm_dir, "*")))


async def _control() -> None:
    """Without publish_transports: HTTP delivery, and no SHM channel created."""
    workdir = tempfile.mkdtemp(prefix="pt-control-")
    shm_dir = os.path.join(workdir, "shm")
    os.makedirs(shm_dir, exist_ok=True)
    try:
        base, source = await _make_passthrough(workdir, None)

        received: List[RawData] = []
        arrived = asyncio.Event()

        async def on_data(rd: RawData) -> None:
            received.append(rd)
            arrived.set()

        await base.navigate("dst").navigate(SUBPATH).subscribe(on_data)
        await asyncio.sleep(0.5)
        await source.publish(RawData(content=PAYLOAD, content_type=CONTENT_TYPE))

        await asyncio.wait_for(arrived.wait(), timeout=RECEIVE_TIMEOUT)
        assert received[0].content == PAYLOAD, "HTTP payload mismatch"
        assert not _shm_artifacts(shm_dir), "SHM channel created without publish_transports"
        print("  control : delivered over HTTP, no SHM channel  -> OK")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def _shm_only() -> None:
    """With shm_only=True: SHM round-trip, and nothing on the HTTP path."""
    workdir = tempfile.mkdtemp(prefix="pt-shm-")
    shm_dir = os.path.join(workdir, "shm")
    os.makedirs(shm_dir, exist_ok=True)
    shm_path = os.path.join(shm_dir, "front_center")
    try:
        base, source = await _make_passthrough(
            workdir,
            {SUBPATH: PassthroughPublisherTransport(shm_path=shm_path, shm_only=True)},
        )

        from_shm: List[RawData] = []
        from_http: List[RawData] = []
        arrived = asyncio.Event()

        async def on_shm(rd: RawData) -> None:
            from_shm.append(rd)
            arrived.set()

        async def on_http(rd: RawData) -> None:
            from_http.append(rd)

        subscription = create_shm_subscription(on_shm, shm_path=shm_path, queue_size=4)
        await base.navigate("dst").navigate(SUBPATH).subscribe(on_http)
        await asyncio.sleep(0.5)

        await source.publish(RawData(content=PAYLOAD, content_type=CONTENT_TYPE))
        await asyncio.wait_for(arrived.wait(), timeout=RECEIVE_TIMEOUT)

        assert from_shm[0].content == PAYLOAD, "SHM payload mismatch"
        assert from_shm[0].content_type == CONTENT_TYPE, (
            f"SHM envelope lost the content type: {from_shm[0].content_type!r}"
        )
        assert _shm_artifacts(shm_dir), "no SHM channel was created"

        # shm_only must suppress the HTTP path, otherwise a silent fallback to
        # HTTP would be indistinguishable from a working SHM transport.
        await asyncio.sleep(NEGATIVE_TIMEOUT)
        assert not from_http, "shm_only=True still delivered over HTTP"

        print(f"  shm_only: round-tripped {len(from_shm[0].content)} B via SHM "
              f"({', '.join(_shm_artifacts(shm_dir))}), HTTP suppressed  -> OK")
        try:
            await subscription.unsubscribe()
        except Exception:
            pass
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_passthrough_without_transport_uses_http() -> None:
    asyncio.run(_control())


def test_passthrough_shm_only_round_trip() -> None:
    asyncio.run(_shm_only())


if __name__ == "__main__":
    print("DTPSPassthrough shared-memory transport")
    test_passthrough_without_transport_uses_http()
    test_passthrough_shm_only_round_trip()
    print("  all passed")
