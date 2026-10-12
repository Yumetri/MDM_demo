from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.network_log_repository import NetworkLogRepository
from mdm_demo.application.ports.repositories.network_repository import NetworkRepository
from mdm_demo.infrastructure.persistence.repositories.network_log_repository import (
    SqlAlchemyNetworkLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.network_repository import (
    SqlAlchemyNetworkRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyNetworkUnitOfWork(SqlAlchemyUnitOfWork):
    networks: NetworkRepository
    network_logs: NetworkLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.networks = SqlAlchemyNetworkRepository(session)
        self.network_logs = SqlAlchemyNetworkLogRepository(session)
