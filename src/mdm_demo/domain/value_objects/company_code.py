import re
from dataclasses import dataclass

from mdm_demo.domain.errors import AutoCodeUnavailable, InvalidCompanyValue
from mdm_demo.domain.value_objects.company_name import CompanyName


@dataclass(frozen=True)
class CompanyCode:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z]{3}", self.value) is None:
            raise InvalidCompanyValue("code")
        object.__setattr__(self, "value", self.value.upper())

    @classmethod
    def from_name(cls, name: CompanyName) -> "CompanyCode":
        letters = re.sub(r"[^A-Za-z]", "", name.value)
        if len(letters) < 3:
            raise AutoCodeUnavailable
        return cls(letters[:3])
