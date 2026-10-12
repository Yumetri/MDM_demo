import re
from dataclasses import dataclass

from mdm_demo.domain.errors.year import InvalidYearValue
from mdm_demo.domain.value_objects.year_value import YearValue


@dataclass(frozen=True)
class YearCode:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(r"[0-9]{4}", self.value) is None:
            raise InvalidYearValue("year")
        YearValue(int(self.value))

    @classmethod
    def from_year(cls, year: YearValue) -> "YearCode":
        return cls(str(year.value))
