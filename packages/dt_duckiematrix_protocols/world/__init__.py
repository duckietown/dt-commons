from cbor2 import dumps, loads


class CBor2Message:

    def as_dict(self) -> dict:
        return self.__dict__

    def to_bytes(self) -> bytes:
        return dumps(self.as_dict())

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CBor2Message':
        return cls(**loads(data))
