from uuid import UUID

from mdm_demo.application.ports.cursors.memory import MemoryBoundary, MemoryLogBoundary
from mdm_demo.infrastructure.pagination.memory_cursor import SignedMemoryCursor


class SignedMemoryLogCursor:
    def __init__(self, key: str) -> None:
        # Validate configuration at construction, including before the first request.
        SignedMemoryCursor(key)
        self._key = key

    def _codec(self, memory_id: UUID) -> SignedMemoryCursor:
        return SignedMemoryCursor(self._key, query=f"memory_logs:{memory_id}:occurred_at,id:asc")

    def encode(self, boundary: MemoryLogBoundary, memory_id: UUID) -> str:
        return self._codec(memory_id).encode(MemoryBoundary(boundary.occurred_at, boundary.id))

    def decode(self, token: str, memory_id: UUID) -> MemoryLogBoundary:
        boundary = self._codec(memory_id).decode(token)
        return MemoryLogBoundary(boundary.created_at, boundary.id)
