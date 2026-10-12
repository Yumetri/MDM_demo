from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.year_log_repository import YearLogRepository
from mdm_demo.application.ports.repositories.year_repository import YearRepository
from mdm_demo.infrastructure.persistence.repositories.year_log_repository import (
    SqlAlchemyYearLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.year_repository import (
    SqlAlchemyYearRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyYearUnitOfWork(SqlAlchemyUnitOfWork):
    years: YearRepository
    year_logs: YearLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.years = SqlAlchemyYearRepository(session)
        self.year_logs = SqlAlchemyYearLogRepository(session)
