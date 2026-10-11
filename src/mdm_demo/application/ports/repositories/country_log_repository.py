from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.country import CountryLogBoundary
from mdm_demo.domain.entities.country_log import CountryLog


class CountryLogRepository(Protocol):
    async def add(self, log: CountryLog) -> None: ...
    async def get(self, log_id: UUID) -> CountryLog | None: ...
    async def list(
        self, country_id: UUID, boundary: CountryLogBoundary | None, limit: int
    ) -> list[CountryLog]: ...
