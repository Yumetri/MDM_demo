from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.company import Company


@dataclass(frozen=True)
class CompanyDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, company: Company) -> "CompanyDTO":
        return cls(
            company.id,
            company.name.value,
            company.code.value,
            company.created_at,
            company.updated_at,
        )


@dataclass(frozen=True)
class CompanyPage:
    items: list[CompanyDTO]
    next_cursor: str | None
    has_next: bool
