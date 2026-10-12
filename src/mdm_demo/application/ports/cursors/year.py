from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class YearBoundary:
    year: int


class YearCursor(Protocol):
    def encode(self, boundary: YearBoundary) -> str: ...
    def decode(self, token: str) -> YearBoundary: ...


@dataclass(frozen=True)
class YearLogBoundary:
    occurred_at: datetime
    id: UUID


class YearLogCursor(Protocol):
    def encode(self, boundary: YearLogBoundary, year_id: UUID) -> str: ...
    def decode(self, token: str, year_id: UUID) -> YearLogBoundary: ...
