from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.memory import MemoryLogBoundary
from mdm_demo.domain.entities.memory_log import MemoryLog


class MemoryLogRepository(Protocol):
    async def add(self, log: MemoryLog) -> None: ...
    async def get(self, log_id: UUID) -> MemoryLog | None: ...
    async def list(
        self, memory_id: UUID, boundary: MemoryLogBoundary | None, limit: int
    ) -> list[MemoryLog]: ...
