from dataclasses import dataclass
from unicodedata import normalize

from mdm_demo.domain.errors.country import InvalidCountryValue


@dataclass(frozen=True)
class CountryName:
    value: str

    def __post_init__(self) -> None:
        value = normalize("NFC", self.value.strip().upper())
        if not 1 <= len(value) <= 100 or "\x00" in value:
            raise InvalidCountryValue("name")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidCountryValue("name") from exc
        object.__setattr__(self, "value", value)
