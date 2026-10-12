from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.memory import Memory


@dataclass(frozen=True)
class MemoryDTO:
    id: UUID
    capacity: int
    unit: str
    code: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, memory: Memory) -> "MemoryDTO":
        return cls(
            memory.id,
            memory.size.capacity,
            memory.size.unit,
            memory.size.code,
            memory.created_at,
            memory.updated_at,
        )


@dataclass(frozen=True)
class MemoryPage:
    items: list[MemoryDTO]
    next_cursor: str | None
    has_next: bool
