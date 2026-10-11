from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.model import ModelLogBoundary
from mdm_demo.domain.entities.model_log import ModelLog


class ModelLogRepository(Protocol):
    async def add(self, log: ModelLog) -> None: ...
    async def get(self, log_id: UUID) -> ModelLog | None: ...
    async def list(
        self, model_id: UUID, boundary: ModelLogBoundary | None, limit: int
    ) -> list[ModelLog]: ...
