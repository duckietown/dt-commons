from cbor2 import dumps, loads


class CBorMessage:

    def as_dict(self) -> dict:
        return self.__dict__

    def to_bytes(self) -> bytes:
        return dumps(self.as_dict())

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CBorMessage':
        d = loads(data)
        d.pop("_t", None)
        return cls(**d)
