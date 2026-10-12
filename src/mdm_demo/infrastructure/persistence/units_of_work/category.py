from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.category_log_repository import CategoryLogRepository
from mdm_demo.application.ports.repositories.category_repository import CategoryRepository
from mdm_demo.infrastructure.persistence.repositories.category_log_repository import (
    SqlAlchemyCategoryLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyCategoryUnitOfWork(SqlAlchemyUnitOfWork):
    categories: CategoryRepository
    category_logs: CategoryLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.categories = SqlAlchemyCategoryRepository(session)
        self.category_logs = SqlAlchemyCategoryLogRepository(session)
