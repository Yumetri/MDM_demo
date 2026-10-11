from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.brand import Brand


@dataclass(frozen=True)
class BrandDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, brand: Brand) -> "BrandDTO":
        return cls(
            brand.id,
            brand.name.value,
            brand.code.value,
            brand.created_at,
            brand.updated_at,
        )


@dataclass(frozen=True)
class BrandPage:
    items: list[BrandDTO]
    next_cursor: str | None
    has_next: bool
