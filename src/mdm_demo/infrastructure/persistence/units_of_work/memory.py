from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.memory_log_repository import MemoryLogRepository
from mdm_demo.application.ports.repositories.memory_repository import MemoryRepository
from mdm_demo.infrastructure.persistence.repositories.memory_log_repository import (
    SqlAlchemyMemoryLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.memory_repository import (
    SqlAlchemyMemoryRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyMemoryUnitOfWork(SqlAlchemyUnitOfWork):
    memories: MemoryRepository
    memory_logs: MemoryLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.memories = SqlAlchemyMemoryRepository(session)
        self.memory_logs = SqlAlchemyMemoryLogRepository(session)
