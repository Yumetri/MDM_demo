from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from mdm_demo.domain.entities.company_log import CompanyLog, Operation


@dataclass(frozen=True)
class CompanyLogDTO:
    id: UUID
    company_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: dict[str, str] | None
    after: dict[str, str] | None

    @classmethod
    def from_entity(cls, log: CompanyLog) -> "CompanyLogDTO":
        return cls(
            log.id,
            log.company_id,
            log.operation,
            log.occurred_at,
            log.request_id,
            dict(log.before) if log.before is not None else None,
            dict(log.after) if log.after is not None else None,
        )


@dataclass(frozen=True)
class CompanyLogPage:
    items: list[CompanyLogDTO]
    next_cursor: str | None
    has_next: bool
