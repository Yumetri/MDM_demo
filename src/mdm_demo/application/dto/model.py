from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.model import Model


@dataclass(frozen=True)
class ModelDTO:
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, model: Model) -> "ModelDTO":
        return cls(
            model.id,
            model.name.value,
            model.code.value,
            model.created_at,
            model.updated_at,
        )


@dataclass(frozen=True)
class ModelPage:
    items: list[ModelDTO]
    next_cursor: str | None
    has_next: bool
