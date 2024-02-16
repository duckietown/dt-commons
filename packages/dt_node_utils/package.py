import dataclasses
from pathlib import Path
from typing import Optional, Union

from xml.etree import ElementTree
from xml.etree.ElementTree import Element


@dataclasses.dataclass
class Package:
    path: Union[str, Path]
    __metadata: Element = dataclasses.field(init=False)

    def __post_init__(self):
        # santitize path
        self.path = Path(self.path)
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

    @classmethod
    def is_package(cls, path: Union[str, Path]) -> bool:
        metadata_fpath: Path = Path(path) / "package.xml"
        return metadata_fpath.is_file()

    @classmethod
    def nearest(cls, start: str) -> Optional['Package']:
        path: Path = Path(start)
        root: Path = Path("/")
        while path != root:
            if cls.is_package(path):
                return Package(path)
            path = path.parent
        return None
