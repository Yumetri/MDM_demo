import re
from dataclasses import dataclass

from mdm_demo.domain.errors.country import InvalidCountryValue


@dataclass(frozen=True)
class CountryCode:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z]{3}", self.value.strip()) is None:
            raise InvalidCountryValue("code")
        object.__setattr__(self, "value", self.value.strip().upper())
