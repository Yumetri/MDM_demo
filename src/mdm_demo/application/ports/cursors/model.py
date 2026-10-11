from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ModelBoundary:
    created_at: datetime
    id: UUID


class ModelCursor(Protocol):
    def encode(self, boundary: ModelBoundary) -> str: ...
    def decode(self, token: str) -> ModelBoundary: ...


@dataclass(frozen=True)
class ModelLogBoundary:
    occurred_at: datetime
    id: UUID


class ModelLogCursor(Protocol):
    def encode(self, boundary: ModelLogBoundary, model_id: UUID) -> str: ...
    def decode(self, token: str, model_id: UUID) -> ModelLogBoundary: ...
