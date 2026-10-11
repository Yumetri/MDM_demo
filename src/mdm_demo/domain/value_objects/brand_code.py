import re
from dataclasses import dataclass

from mdm_demo.domain.errors import AutoCodeUnavailable, InvalidBrandValue
from mdm_demo.domain.value_objects.brand_name import BrandName


@dataclass(frozen=True)
class BrandCode:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9]{3}", self.value.strip()) is None:
            raise InvalidBrandValue("code")
        object.__setattr__(self, "value", self.value.strip().upper())

    @classmethod
    def from_name(cls, name: BrandName) -> "BrandCode":
        letters = re.sub(r"[^A-Za-z0-9]", "", name.value)
        if len(letters) < 3:
            raise AutoCodeUnavailable
        return cls(letters[:3])
