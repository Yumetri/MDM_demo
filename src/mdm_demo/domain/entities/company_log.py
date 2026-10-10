from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal
from uuid import UUID, uuid4

Operation = Literal["create", "update", "delete"]


@dataclass(frozen=True, eq=False)
class CompanyLog:
    id: UUID
    company_id: UUID
    operation: Operation
    occurred_at: datetime
    request_id: UUID
    before: Mapping[str, str] | None
    after: Mapping[str, str] | None

    def __post_init__(self) -> None:
        valid = {
            "create": self.before is None and self.after is not None,
            "update": self.before is not None and self.after is not None,
            "delete": self.before is not None and self.after is None,
        }
        if not valid.get(self.operation, False):
            raise ValueError("Invalid log snapshots")
        for field in ("before", "after"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, MappingProxyType(dict(value)))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompanyLog) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def record(
        cls,
        company_id: UUID,
        operation: Operation,
        request_id: UUID,
        before: Mapping[str, str] | None,
        after: Mapping[str, str] | None,
    ) -> "CompanyLog":
        return cls(uuid4(), company_id, operation, datetime.now(UTC), request_id, before, after)
