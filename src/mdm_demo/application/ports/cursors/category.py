from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CategoryBoundary:
    created_at: datetime
    id: UUID


class CategoryCursor(Protocol):
    def encode(self, boundary: CategoryBoundary) -> str: ...
    def decode(self, token: str) -> CategoryBoundary: ...


@dataclass(frozen=True)
class CategoryLogBoundary:
    occurred_at: datetime
    id: UUID


class CategoryLogCursor(Protocol):
    def encode(self, boundary: CategoryLogBoundary, category_id: UUID) -> str: ...
    def decode(self, token: str, category_id: UUID) -> CategoryLogBoundary: ...
