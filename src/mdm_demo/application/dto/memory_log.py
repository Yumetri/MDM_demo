from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.memory_log import MemoryLog, Operation


@dataclass(frozen=True)
class MemoryLogDTO:
    id: UUID
    memory_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str | int] | None
    after: dict[str, str | int] | None

    @classmethod
    def from_entity(cls, log: MemoryLog) -> "MemoryLogDTO":
        return cls(
            log.id,
            log.memory_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class MemoryLogPage:
    items: list[MemoryLogDTO]
    next_cursor: str | None
    has_next: bool
