from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.category import Category


@dataclass(frozen=True)
class CategoryDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, category: Category) -> "CategoryDTO":
        return cls(
            category.id,
            category.name.value,
            category.code.value,
            category.created_at,
            category.updated_at,
        )


@dataclass(frozen=True)
class CategoryPage:
    items: list[CategoryDTO]
    next_cursor: str | None
    has_next: bool
