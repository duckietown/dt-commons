from cbor2 import dumps


class CBor2Message:

    def as_dict(self) -> dict:
        return self.__dict__

    def to_bytes(self) -> bytes:
        return dumps(self.as_dict())
