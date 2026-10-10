from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CompanyBoundary:
    created_at: datetime
    id: UUID


class CompanyCursor(Protocol):
    def encode(self, boundary: CompanyBoundary) -> str: ...
    def decode(self, token: str) -> CompanyBoundary: ...


@dataclass(frozen=True)
class CompanyLogBoundary:
    occurred_at: datetime
    id: UUID


class CompanyLogCursor(Protocol):
    def encode(self, boundary: CompanyLogBoundary, company_id: UUID) -> str: ...
    def decode(self, token: str, company_id: UUID) -> CompanyLogBoundary: ...
