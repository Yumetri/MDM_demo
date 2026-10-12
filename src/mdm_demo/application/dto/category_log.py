from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.category_log import CategoryLog, Operation


@dataclass(frozen=True)
class CategoryLogDTO:
    id: UUID
    category_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str] | None
    after: dict[str, str] | None

    @classmethod
    def from_entity(cls, log: CategoryLog) -> "CategoryLogDTO":
        return cls(
            log.id,
            log.category_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class CategoryLogPage:
    items: list[CategoryLogDTO]
    next_cursor: str | None
    has_next: bool
