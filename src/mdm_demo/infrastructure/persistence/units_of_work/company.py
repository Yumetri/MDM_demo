from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.infrastructure.persistence.repositories.company_log_repository import (
    SqlAlchemyCompanyLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyCompanyUnitOfWork(SqlAlchemyUnitOfWork):
    companies: CompanyRepository
    company_logs: CompanyLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.companies = SqlAlchemyCompanyRepository(session)
        self.company_logs = SqlAlchemyCompanyLogRepository(session)
