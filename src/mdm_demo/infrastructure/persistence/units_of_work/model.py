from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.model_log_repository import ModelLogRepository
from mdm_demo.application.ports.repositories.model_repository import ModelRepository
from mdm_demo.infrastructure.persistence.repositories.model_log_repository import (
    SqlAlchemyModelLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.model_repository import (
    SqlAlchemyModelRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyModelUnitOfWork(SqlAlchemyUnitOfWork):
    models: ModelRepository
    model_logs: ModelLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.models = SqlAlchemyModelRepository(session)
        self.model_logs = SqlAlchemyModelLogRepository(session)
