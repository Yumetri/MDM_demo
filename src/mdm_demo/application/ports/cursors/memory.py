from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class MemoryBoundary:
    created_at: datetime
    id: UUID


class MemoryCursor(Protocol):
    def encode(self, boundary: MemoryBoundary) -> str: ...
    def decode(self, token: str) -> MemoryBoundary: ...


@dataclass(frozen=True)
class MemoryLogBoundary:
    occurred_at: datetime
    id: UUID


class MemoryLogCursor(Protocol):
    def encode(self, boundary: MemoryLogBoundary, memory_id: UUID) -> str: ...
    def decode(self, token: str, memory_id: UUID) -> MemoryLogBoundary: ...
