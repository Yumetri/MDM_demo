from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.country import Country


@dataclass(frozen=True)
class CountryDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, country: Country) -> "CountryDTO":
        return cls(
            country.id,
            country.name.value,
            country.code.value,
            country.created_at,
            country.updated_at,
        )


@dataclass(frozen=True)
class CountryPage:
    items: list[CountryDTO]
    next_cursor: str | None
    has_next: bool
