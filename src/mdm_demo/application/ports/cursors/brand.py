from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class BrandBoundary:
    created_at: datetime
    id: UUID


class BrandCursor(Protocol):
    def encode(self, boundary: BrandBoundary) -> str: ...
    def decode(self, token: str) -> BrandBoundary: ...


@dataclass(frozen=True)
class BrandLogBoundary:
    occurred_at: datetime
    id: UUID


class BrandLogCursor(Protocol):
    def encode(self, boundary: BrandLogBoundary, brand_id: UUID) -> str: ...
    def decode(self, token: str, brand_id: UUID) -> BrandLogBoundary: ...
