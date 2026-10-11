from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursor import BrandLogBoundary
from mdm_demo.domain.entities.brand_log import BrandLog


class BrandLogRepository(Protocol):
    async def add(self, log: BrandLog) -> None: ...
    async def get(self, log_id: UUID) -> BrandLog | None: ...
    async def list(
        self, brand_id: UUID, boundary: BrandLogBoundary | None, limit: int
    ) -> list[BrandLog]: ...
