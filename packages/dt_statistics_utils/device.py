import json
import os.path
import time
from typing import Optional

EVENTS_DIR: str = "/data/stats/events"


def log_event(type: str, data: Optional[dict] = None, stamp: Optional[float] = None):
    if not os.path.isdir(EVENTS_DIR):
        print(f"WARNING: could not write Event to disk. Directory '{EVENTS_DIR}' not found.")
        return
    # sanitize 'stamp'
    if stamp is None:
        stamp = time.time()
    # events store timestamps in nanoseconds
    stamp = int(stamp * (10**9))
    # sanitize 'data'
    if data is None:
        data = {}
    else:
        # make sure the given data can be serialized in JSON
        _ = json.dumps(data)
    # last check of everything
    assert isinstance(type, str)
    assert isinstance(data, dict)
    assert isinstance(stamp, int)
    # compile content
    content = json.dumps({"type": type, "stamp": stamp, "data": data})
    filepath = os.path.join(EVENTS_DIR, f"{stamp}.json")
    # write file to disk
    with open(filepath, "wt") as fout:
        try:
            fout.write(content)
        except Exception as e:
            print(f"WARNING: could not write Event to disk. Error: {str(e)}")
