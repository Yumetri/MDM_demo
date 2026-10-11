from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CountryBoundary:
    created_at: datetime
    id: UUID


class CountryCursor(Protocol):
    def encode(self, boundary: CountryBoundary) -> str: ...
    def decode(self, token: str) -> CountryBoundary: ...


@dataclass(frozen=True)
class CountryLogBoundary:
    occurred_at: datetime
    id: UUID


class CountryLogCursor(Protocol):
    def encode(self, boundary: CountryLogBoundary, country_id: UUID) -> str: ...
    def decode(self, token: str, country_id: UUID) -> CountryLogBoundary: ...
