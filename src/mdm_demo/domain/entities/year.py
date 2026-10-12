from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.errors.year import InvalidYearValue
from mdm_demo.domain.value_objects.year_code import YearCode
from mdm_demo.domain.value_objects.year_value import YearValue


@dataclass(frozen=True, eq=False)
class Year:
    id: UUID
    year: YearValue
    code: YearCode
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.code != YearCode.from_year(self.year):
            raise InvalidYearValue("year")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Year) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, year: int) -> "Year":
        value = YearValue(year)
        now = datetime.now(UTC)
        return cls(uuid4(), value, YearCode.from_year(value), now, now)

    def change_year(self, year: int) -> bool:
        value = YearValue(year)
        if value == self.year:
            return False
        code = YearCode.from_year(value)
        object.__setattr__(self, "year", value)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "updated_at", datetime.now(UTC))
        return True

    def snapshot(self) -> dict[str, str | int]:
        return {"id": str(self.id), "year": self.year.value, "code": self.code.value}
