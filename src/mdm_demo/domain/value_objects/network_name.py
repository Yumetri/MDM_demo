from dataclasses import dataclass
from unicodedata import normalize

from mdm_demo.domain.errors.network import InvalidNetworkValue


@dataclass(frozen=True)
class NetworkName:
    value: str

    def __post_init__(self) -> None:
        value = normalize("NFC", self.value.strip().upper())
        if not 1 <= len(value) <= 100 or "\x00" in value:
            raise InvalidNetworkValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidNetworkValue("name") from exc
        object.__setattr__(self, "value", value)
