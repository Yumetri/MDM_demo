from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.year import Year


@dataclass(frozen=True)
class YearDTO:
    id: UUID
    year: int
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, year: Year) -> "YearDTO":
        return cls(
            year.id,
            year.year.value,
            year.code.value,
            year.created_at,
            year.updated_at,
        )


@dataclass(frozen=True)
class YearPage:
    items: list[YearDTO]
    next_cursor: str | None
    has_next: bool
