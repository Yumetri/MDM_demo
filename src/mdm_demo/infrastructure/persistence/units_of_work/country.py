from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.country_log_repository import CountryLogRepository
from mdm_demo.application.ports.repositories.country_repository import CountryRepository
from mdm_demo.infrastructure.persistence.repositories.country_log_repository import (
    SqlAlchemyCountryLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.country_repository import (
    SqlAlchemyCountryRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyCountryUnitOfWork(SqlAlchemyUnitOfWork):
    countries: CountryRepository
    country_logs: CountryLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.countries = SqlAlchemyCountryRepository(session)
        self.country_logs = SqlAlchemyCountryLogRepository(session)
