import dataclasses
import glob
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union, List

from xml.etree import ElementTree
from xml.etree.ElementTree import Element


@dataclasses.dataclass
class Package:
    path: Union[str, Path]
    __metadata: Element = dataclasses.field(init=False)

    def __post_init__(self):
        # santitize path
        self.path = Path(self.path)
        # we accept package.xml as a pointer as well
        if self.path.name == "package.xml":
            self.path = self.path.parent
        # read metadata file
        metadata_fpath: Path = self.path / "package.xml"
        if not metadata_fpath.is_file():
            raise FileNotFoundError(metadata_fpath)
        tree = ElementTree.parse(metadata_fpath)
        self.__metadata = tree.getroot()

    @property
    def name(self) -> str:
        return self.__metadata.find("name").text

    @property
    def version(self) -> str:
        return self.__metadata.find("version").text

    @property
    def description(self) -> str:
        return self.__metadata.find("description").text

    @property
    def configs_dir(self) -> Path:
        return self.path / "config"

    def has_config(self, config: str) -> bool:
        config: str = f"{config}.yaml" if not config.endswith(".yaml") else config
        return (self.path / "config" / config).is_file()

    def all_configs(self) -> List[str]:
        return [
            os.path.relpath(p, self.configs_dir)[:-5] + "[.yaml]" for p in
            glob.glob(str(self.configs_dir / "**" / "*.yaml"), recursive=True)
        ]

    @classmethod
    def is_package(cls, path: Union[str, Path]) -> bool:
        metadata_fpath: Path = Path(path) / "package.xml"
        return metadata_fpath.is_file()

    @classmethod
    @lru_cache
    def nearest(cls, start: str) -> Optional['Package']:
        path: Path = Path(start)
        root: Path = Path("/")
        while path != root:
            if cls.is_package(path):
                return Package(path)
            path = path.parent
        return None

    @classmethod
    @lru_cache
    def find_all(cls, start: str) -> List['Package']:
        start = os.path.abspath(start)
        return [
            Package(p) for p in glob.glob(os.path.join(start, "**", "package.xml"), recursive=True)
        ]

    @classmethod
    @lru_cache
    def from_name(cls, name: str) -> Optional['Package']:
        if "SOURCE_DIR" not in os.environ:
            raise EnvironmentError("SOURCE_DIR not set")
        for p in cls.find_all(os.path.abspath(os.environ["SOURCE_DIR"])):
            if p.name == name:
                return p
