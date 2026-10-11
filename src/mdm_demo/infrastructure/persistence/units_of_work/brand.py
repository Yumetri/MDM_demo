from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.brand_log_repository import BrandLogRepository
from mdm_demo.application.ports.repositories.brand_repository import BrandRepository
from mdm_demo.infrastructure.persistence.repositories.brand_log_repository import (
    SqlAlchemyBrandLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.brand_repository import (
    SqlAlchemyBrandRepository,
)
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class SqlAlchemyBrandUnitOfWork(SqlAlchemyUnitOfWork):
    brands: BrandRepository
    brand_logs: BrandLogRepository

    def _bind_repositories(self, session: AsyncSession) -> None:
        self.brands = SqlAlchemyBrandRepository(session)
        self.brand_logs = SqlAlchemyBrandLogRepository(session)
