import argparse
import asyncio
import dataclasses
import json
import os
import re
from abc import abstractmethod
from typing import Optional, Dict, Type, Union, List, Set

import yaml

from dt_robot_utils import get_robot_name
from dtps import context, DTPSContext, SubscriptionInterface
from dtps_http import TopicProperties, RawData, TransformError

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 11411

ROBOT_NAME: str = get_robot_name()
EXAMPLE_CREATE_PAYLOAD = {"key": "/example/key/", "value": ["duckietown", "is", "cool"], "persist": False}

FullRW = None
AUTO = None


@dataclasses.dataclass
class FileAdapterTemplate:
    object_path: str
    kind: Type["GenericFileAdapter"]
    properties: Optional[TopicProperties] = AUTO


@dataclasses.dataclass
class GenericFileAdapter:
    file_path: str
    object_path: str
    properties: Optional[TopicProperties]
    persist: bool
    create: bool = False
    initial: Optional[object] = None

    _content: Optional[bytes] = AUTO
    _context: DTPSContext = None
    _subscriber: SubscriptionInterface = None
    
    def __post_init__(self):
        if not os.path.exists(self.file_path):
            if not self.create:
                raise FileNotFoundError(f"File not found: {self.file_path}")
            # make sure we received data
            if self.initial is None:
                raise ValueError("When creating a new file, 'initial' must be provided")
            # create the directory
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            # create the file
            self._content = self.raw_from_native_object(self.initial)
            self.write_to_disk()
        # read the content from disk
        self.read_from_disk()
        # format the content
        self._content = self.raw_from_native_object(self.to_native_object())
        
    def read_from_disk(self):
        if not self.persist:
            return
        with open(self.file_path, "rb") as fin:
            self._content = fin.read()

    def write_to_disk(self):
        if not self.persist:
            return
        with open(self.file_path, "wb") as fout:
            fout.write(self._content)

    def set_content_quietly(self, content: object):
        self._content = self.raw_from_native_object(content)
        self.write_to_disk()

    @abstractmethod
    def to_native_object(self) -> object:
        pass

    @abstractmethod
    def raw_from_native_object(self, obj: object) -> bytes:
        pass

    async def on_update(self, rd: RawData):
        # update the content
        new_content: bytes = self.raw_from_native_object(rd.get_as_native_object())
        # check if the content has changed
        if new_content == self._content:
            return
        # update the content
        self._content = new_content
        # write new content to disk
        self.write_to_disk()

    async def init(self, cxt: DTPSContext):
        self._context = await cxt.navigate(self.object_path).queue_create()
        # publish the initial value
        await self._context.publish(RawData.cbor_from_native_object(self.to_native_object()))
        # subscribe for updates
        if self.properties is FullRW or self.properties.pushable:
            self._subscriber = await self._context.subscribe(self.on_update)

    def to_rawdata(self) -> RawData:
        return RawData.json_from_native_object(self.to_native_object())

    def __str__(self):
        json_str = json.dumps(dataclasses.asdict(self), sort_keys=True)
        return f"{self.__class__.__name__}({json_str[1:-1]})"


@dataclasses.dataclass
class JSONFileAdapter(GenericFileAdapter):

    def to_native_object(self) -> Union[dict, list, str, int, float, bool]:
        return json.loads(self._content.decode("utf-8"))

    def raw_from_native_object(self, obj: Union[dict, list, str, int, float, bool]) -> bytes:
        return json.dumps(obj, sort_keys=True, indent=4).encode("utf-8")


@dataclasses.dataclass
class YAMLFileAdapter(GenericFileAdapter):

    def to_native_object(self) -> Union[dict, list, str, int, float, bool, bytes]:
        return yaml.safe_load(self._content.decode("utf-8"))

    def raw_from_native_object(self, obj: Union[dict, list, str, int, float, bool, bytes]) -> bytes:
        return yaml.dump(obj, sort_keys=True).encode("utf-8")


@dataclasses.dataclass
class PlainFileAdapter(GenericFileAdapter):

    def to_native_object(self) -> str:
        return self._content.decode("utf-8")

    def raw_from_native_object(self, obj: str) -> bytes:
        return obj.encode("utf-8")

    def to_rawdata(self) -> RawData:
        return RawData.simple_string(self.to_native_object())


ADAPTED_FILES_DIR = "/data/config"
ADAPTED_FILES = {
    f"{ADAPTED_FILES_DIR}/node/(?P<key>.*)/{ROBOT_NAME}.yaml": FileAdapterTemplate(
        object_path="config/node/{key}",
        properties=FullRW,
        kind=YAMLFileAdapter,
    ),

    f"{ADAPTED_FILES_DIR}/permissions/(?P<key>.*)": FileAdapterTemplate(
        object_path="config/permission/{key}",
        properties=FullRW,
        kind=PlainFileAdapter,
    ),

    f"{ADAPTED_FILES_DIR}/calibrations/(?P<key>.*)/{ROBOT_NAME}.yaml": FileAdapterTemplate(
        object_path="config/calibration/{key}",
        properties=FullRW,
        kind=YAMLFileAdapter,
    ),

    f"{ADAPTED_FILES_DIR}/calibrations/(?P<key>.*)/default.yaml": FileAdapterTemplate(
        object_path="config/calibration/{key}/default",
        properties=TopicProperties.readonly(),
        kind=YAMLFileAdapter,
    ),

    f"{ADAPTED_FILES_DIR}/robot_(?P<key>.*)": FileAdapterTemplate(
        object_path="config/robot/{key}",
        properties=TopicProperties.readonly(),
        kind=PlainFileAdapter,
    ),

    # match any other YAML file (always leave this as the last item in this dictionary)
    f"{ADAPTED_FILES_DIR}/(?P<key>.*).yaml": FileAdapterTemplate(
        object_path="config/{key}",
        properties=FullRW,
        kind=YAMLFileAdapter,
    ),
}


class KVStore:

    def __init__(self, args: argparse.Namespace):
        self._args: argparse.Namespace = args
        self._cxt: Optional[DTPSContext] = None
        self._adapters: Dict[str, GenericFileAdapter] = {}
        # all files
        files = [os.path.join(dp, f) for dp, dn, fn in os.walk(ADAPTED_FILES_DIR) for f in fn]
        matched: Set[str] = set()
        # process regexed files
        for regex, adapter_template in ADAPTED_FILES.items():
            AdapterClass: Type[GenericFileAdapter] = adapter_template.kind
            pattern = re.compile(f"^{regex}$")
            # find all files matching the pattern
            for file in files:
                if file in matched:
                    continue
                match = pattern.match(file)
                if not match:
                    continue
                groups: Dict[str, str] = match.groupdict()
                # apply groups to the object path
                object_path = adapter_template.object_path.format(**groups)
                # create a new adapter
                # noinspection PyArgumentList
                adapter = AdapterClass(
                    file_path=file,
                    object_path=object_path,
                    properties=adapter_template.properties,
                    persist=True,
                )
                self._adapters[file] = adapter
                matched.add(file)

    async def define(self, rd: RawData):
        # decode request
        data: object = rd.get_as_native_object()
        if not isinstance(data, dict) or "key" not in data or "value" not in data:
            return TransformError(400, f"Expected a payload of the form "
                                       f"'{{\"key\": \"<str>\", \"value\": \"<any>\", \"persist\": \"<bool>\"}}'")

        key: str = data["key"].strip("/")
        value: Union[dict, list, str, int, float, bool, bytes] = data["value"]
        persist: bool = data.get("persist", False)

        if ".." in key:
            return TransformError(400, "Key cannot contain '..'")

        # example key/value
        if key == EXAMPLE_CREATE_PAYLOAD["key"].strip("/"):
            return RawData.json_from_native_object(EXAMPLE_CREATE_PAYLOAD)

        fpath: str = f"{ADAPTED_FILES_DIR}/{key}.yaml"
        if fpath not in self._adapters:
            # create new adapter
            adapter = YAMLFileAdapter(
                file_path=fpath,
                object_path=f"config/{key}",
                properties=FullRW,
                create=True,
                persist=persist,
                initial=value,
            )
            adapter.set_content_quietly(value)
            await adapter.init(self._cxt)
            self._adapters[fpath] = adapter
        else:
            pass
        # ---
        return RawData.json_from_native_object(EXAMPLE_CREATE_PAYLOAD)

    async def run(self):
        self._cxt = await context("kvstore", urls=self.urls(self._args))
        # initialize all adapters
        for adapter in self._adapters.values():
            await adapter.init(self._cxt)
        # add 'define' rpc
        define = await self._cxt.navigate("define").queue_create(transform=self.define)
        await define.publish(RawData.json_from_native_object(EXAMPLE_CREATE_PAYLOAD))
        # keep running
        try:
            while True:
                await asyncio.sleep(1.0)
        except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            pass

    @staticmethod
    def urls(args: argparse.Namespace):
        return [
            f"create:http://{args.host}:{args.port}/",
            f"create:http+unix://%2Fdtps%2Fkvstore.sock/"
        ]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", default=DEFAULT_PORT, help="Port to bind to")
    parsed = parser.parse_args()
    # ---
    kvstore = KVStore(parsed)
    try:
        asyncio.run(kvstore.run())
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        pass
