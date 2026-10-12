from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class NetworkBoundary:
    created_at: datetime
    id: UUID


class NetworkCursor(Protocol):
    def encode(self, boundary: NetworkBoundary) -> str: ...
    def decode(self, token: str) -> NetworkBoundary: ...


@dataclass(frozen=True)
class NetworkLogBoundary:
    occurred_at: datetime
    id: UUID


class NetworkLogCursor(Protocol):
    def encode(self, boundary: NetworkLogBoundary, network_id: UUID) -> str: ...
    def decode(self, token: str, network_id: UUID) -> NetworkLogBoundary: ...
