import os
from typing import List, Dict
from urllib.parse import quote

TMPFS_DISK_LOCATION: str = "/data/ramdisk"
DEFAULT_DTPS_UNIX_SOCKET_LOCATION: str = os.path.join(TMPFS_DISK_LOCATION, "dtps")
DTPS_NODES_PREFIX: str = "node"
DTPS_BASE = "DTPS_BASE"


def default_context_env(context_name: str, pure: bool = False,
                        unix_socket_location: str = DEFAULT_DTPS_UNIX_SOCKET_LOCATION) -> dict:
    default_urls: List[str] = default_context_urls(unix_socket_location=unix_socket_location)
    urls: Dict[str, str] = {
        f"{DTPS_BASE}_{context_name.upper()}_{i}": url for i, url in enumerate(default_urls)
    }
    env: dict = {
        **urls
    }
    if not pure:
        env.update(os.environ)
    return env


def default_context_urls(unix_socket_location: str = DEFAULT_DTPS_UNIX_SOCKET_LOCATION) -> List[str]:
    urls: List[str] = [
        # TODO: port should be 0 (randomly assigned by the OS)
        "create:http://0.0.0.0:2333/",
    ]
    if unix_socket_location != DEFAULT_DTPS_UNIX_SOCKET_LOCATION or os.path.exists(TMPFS_DISK_LOCATION):
        if not os.path.exists(unix_socket_location):
            os.makedirs(unix_socket_location, exist_ok=True)
        urls += [
            f"create:http+unix://{quote(os.path.join(unix_socket_location, DTPS_NODES_PREFIX), safe='')}/"
        ]
    # ---
    return urls
