import json
import os
from abc import abstractmethod
from pathlib import Path
from threading import Semaphore
from typing import Any, Optional, Union, MutableMapping, Tuple

import yaml
import cbor2
import jsonschema
import dataclasses
from dataclasses_json import DataClassJsonMixin

from dt_node_utils.package import Package
from dtps import DTPSContext
from dtps_http import RawData, TransformError


class YAMLFileBackend:

    def __init__(self, file_path: str):
        self._file_path: str = file_path
        self._lock: Semaphore = Semaphore()
        self._schema: Optional[dict] = self._load_schema()

    @property
    def schema(self) -> Optional[dict]:
        return self._schema

    def validate(self, data: dict):
        # TODO: debug only
        # print("validating", data, self._schema)
        if self._schema is None:
            return
        jsonschema.validate(data, self._schema)

    def update(self, data: dict):
        # validate the data
        self.validate(data)
        # write to disk
        self.write(data)

    def read(self) -> dict:
        with open(self._file_path, 'r') as file:
            return yaml.safe_load(file)

    def write(self, data: MutableMapping, lock: bool = True):
        if lock:
            self._lock.acquire()
        try:
            # TODO: debug only
            # print("DUMPING: ", yaml.dump(data, None, default_flow_style=True))
            with open(self._file_path, 'w') as file:
                yaml.dump(data, file, default_flow_style=False)
        finally:
            if lock:
                self._lock.release()

    def _load_schema(self) -> Optional[dict]:
        schema_path = self._file_path + ".schema"
        if not os.path.exists(schema_path):
            return None
        with open(schema_path, 'r') as file:
            return json.load(file)


class YAMLFileFrontend:

    def __init__(self, cxt: DTPSContext, container: 'DataContainer'):
        self._container: DataContainer = container
        self._cxt: DTPSContext = cxt
        self._last: Optional[dict] = None

    @property
    def cxt(self) -> DTPSContext:
        return self._cxt

    async def publish(self, data: dict, path: Tuple[str, ...] = None):
        path: Tuple[str, ...] = path if path is not None else ()
        # do not publish if there are no changes
        if cbor2.dumps(data) == cbor2.dumps(self._last):
            return
        # navigate to the path
        cxt = self._cxt
        if path:
            cxt = self._cxt.navigate(*path)
        # publish the data
        # TODO: debug only
        # print("publishing", path, data)
        await cxt.publish(RawData.cbor_from_native_object(data))
        # keep track of the last published data
        self._last = data

    async def expose(self):
        async def transform(rd: RawData, /) -> Union[RawData, TransformError]:
            try:
                data = rd.get_as_native_object()
                if not isinstance(data, dict):
                    return TransformError(400, "Given data is not a dict")
                # validate data
                try:
                    self._container.validate(data)
                except jsonschema.ValidationError as e:
                    return TransformError(400, str(e))
                # update the data container
                self._container.update(data)
            except Exception as e:
                return TransformError(500, str(e))
            # return the same data
            return rd

        await self._cxt.queue_create(transform=transform)

        await self.publish(self._container.to_dict())


class DataContainer:

    @staticmethod
    def _update_dataclass(base: Any, new: Any):
        if not dataclasses.is_dataclass(base):
            raise ValueError(f"Expected a dataclass, got {type(base)}")
        if not dataclasses.is_dataclass(base):
            raise ValueError(f"Expected a dataclass, got {type(new)}")
        if type(base) is not type(new):
            raise ValueError(f"Expected a dataclass of type {type(base)}, got {type(new)}")
        dataclass_cls = type(base)
        for f in dataclasses.fields(dataclass_cls):
            base1 = getattr(base, f.name)
            new1 = getattr(new, f.name)
            if isinstance(base1, dict):
                DataContainer._update_dict(base1, new1)
            elif isinstance(base1, list):
                DataContainer._update_list(base1, new1)
            elif dataclasses.is_dataclass(base1):
                DataContainer._update_dataclass(base1, new1)
            else:
                setattr(base, f.name, new1)

    @staticmethod
    def _update_dict(base: dict, new: dict):
        for k, v in new.items():
            if k in base:
                if isinstance(base[k], dict):
                    DataContainer._update_dict(base[k], v)
                elif isinstance(base[k], list):
                    DataContainer._update_list(base[k], v)
                elif dataclasses.is_dataclass(base[k]):
                    DataContainer._update_dataclass(base[k], v)
                else:
                    base[k] = v
            else:
                base[k] = v

    @staticmethod
    def _update_list(base: list, new: list):
        base.clear()
        base.extend(new)

    def update(self, data: dict):
        # noinspection PyUnresolvedReferences
        new = type(self).from_dict(data)
        DataContainer._update_dataclass(self, new)
        self.on_updated()

    def on_updated(self):
        pass

    @abstractmethod
    def validate(self, data: dict):
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class NodeConfiguration(DataClassJsonMixin, DataContainer):

    def __init__(self):
        DataContainer.__init__(self)
        DataClassJsonMixin.__init__(self)
        self.__backend__: Optional[YAMLFileBackend] = None
        self.__frontend__: Optional[YAMLFileFrontend] = None

    def __post_init__(self):
        NodeConfiguration.__init__(self)

    @classmethod
    def from_name(cls, package: Package, name: str):
        fpath: Path = package.path / "config" / (name if name.endswith(".yaml") else f"{name}.yaml")
        if not fpath.is_file():
            raise FileNotFoundError(f"Configuration file '{fpath}' not found")
        return cls.from_file(fpath.as_posix())

    @classmethod
    def from_file(cls, file_path: str) -> Any:
        backend = YAMLFileBackend(file_path)
        instance = cls.from_dict(backend.read())
        instance.__backend__ = backend
        return instance

    async def expose(self, cxt: DTPSContext):
        self.__frontend__ = YAMLFileFrontend(cxt, self)
        await self.__frontend__.expose()

    def validate(self, data: dict):
        return self.__backend__.validate(data)

    def on_updated(self):
        self.__backend__.update(self.to_dict())

    # noinspection PyMethodOverriding
    def to_dict(self) -> dict:
        return super().to_dict()
