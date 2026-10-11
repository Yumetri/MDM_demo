from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.country_log import CountryLog, Operation


@dataclass(frozen=True)
class CountryLogDTO:
    id: UUID
    country_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str] | None
    after: dict[str, str] | None

    @classmethod
    def from_entity(cls, log: CountryLog) -> "CountryLogDTO":
        return cls(
            log.id,
            log.country_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class CountryLogPage:
    items: list[CountryLogDTO]
    next_cursor: str | None
    has_next: bool
