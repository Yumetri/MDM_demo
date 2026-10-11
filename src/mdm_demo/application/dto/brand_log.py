from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.brand_log import BrandLog, Operation


@dataclass(frozen=True)
class BrandLogDTO:
    id: UUID
    brand_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str] | None
    after: dict[str, str] | None

    @classmethod
    def from_entity(cls, log: BrandLog) -> "BrandLogDTO":
        return cls(
            log.id,
            log.brand_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class BrandLogPage:
    items: list[BrandLogDTO]
    next_cursor: str | None
    has_next: bool
