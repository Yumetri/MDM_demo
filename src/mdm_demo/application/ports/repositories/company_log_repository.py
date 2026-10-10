from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursor import CompanyLogBoundary
from mdm_demo.domain.entities.company_log import CompanyLog


class CompanyLogRepository(Protocol):
    async def add(self, log: CompanyLog) -> None: ...
    async def get(self, log_id: UUID) -> CompanyLog | None: ...
    async def list(
        self, company_id: UUID, boundary: CompanyLogBoundary | None, limit: int
    ) -> list[CompanyLog]: ...
