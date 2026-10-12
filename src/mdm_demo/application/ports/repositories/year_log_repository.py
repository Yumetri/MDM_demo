from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.year import YearLogBoundary
from mdm_demo.domain.entities.year_log import YearLog


class YearLogRepository(Protocol):
    async def add(self, log: YearLog) -> None: ...
    async def get(self, log_id: UUID) -> YearLog | None: ...
    async def list(
        self, year_id: UUID, boundary: YearLogBoundary | None, limit: int
    ) -> list[YearLog]: ...
