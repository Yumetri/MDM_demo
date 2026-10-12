from dataclasses import dataclass

from mdm_demo.domain.errors.year import InvalidYearValue


@dataclass(frozen=True)
class YearValue:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 1900 <= self.value <= 2999:
            raise InvalidYearValue("year")
