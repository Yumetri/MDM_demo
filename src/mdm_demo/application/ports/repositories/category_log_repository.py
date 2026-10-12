from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.category import CategoryLogBoundary
from mdm_demo.domain.entities.category_log import CategoryLog


class CategoryLogRepository(Protocol):
    async def add(self, log: CategoryLog) -> None: ...
    async def get(self, log_id: UUID) -> CategoryLog | None: ...
    async def list(
        self, category_id: UUID, boundary: CategoryLogBoundary | None, limit: int
    ) -> list[CategoryLog]: ...
