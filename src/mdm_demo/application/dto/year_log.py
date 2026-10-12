from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.year_log import Operation, YearLog


@dataclass(frozen=True)
class YearLogDTO:
    id: UUID
    year_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str | int] | None
    after: dict[str, str | int] | None

    @classmethod
    def from_entity(cls, log: YearLog) -> "YearLogDTO":
        return cls(
            log.id,
            log.year_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class YearLogPage:
    items: list[YearLogDTO]
    next_cursor: str | None
    has_next: bool
