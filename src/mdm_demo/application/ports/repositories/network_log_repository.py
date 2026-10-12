from typing import Protocol
from uuid import UUID

from mdm_demo.application.ports.cursors.network import NetworkLogBoundary
from mdm_demo.domain.entities.network_log import NetworkLog


class NetworkLogRepository(Protocol):
    async def add(self, log: NetworkLog) -> None: ...
    async def get(self, log_id: UUID) -> NetworkLog | None: ...
    async def list(
        self, network_id: UUID, boundary: NetworkLogBoundary | None, limit: int
    ) -> list[NetworkLog]: ...
