import re
from dataclasses import dataclass

from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.network import InvalidNetworkValue
from mdm_demo.domain.value_objects.network_name import NetworkName


@dataclass(frozen=True)
class NetworkCode:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if re.fullmatch(r"[A-Za-z0-9]{1,20}", value) is None:
            raise InvalidNetworkValue("code")
        object.__setattr__(self, "value", value.upper())

    @classmethod
    def from_name(cls, name: NetworkName) -> "NetworkCode":
        value = re.sub(r"[^A-Z0-9]", "", name.value)
        if not 1 <= len(value) <= 20:
            raise AutoCodeUnavailable
        return cls(value)
