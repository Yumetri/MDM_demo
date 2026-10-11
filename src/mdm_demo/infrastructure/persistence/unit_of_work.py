import asyncio
from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.brand_log_repository import BrandLogRepository
from mdm_demo.application.ports.repositories.brand_repository import BrandRepository
from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.application.ports.repositories.country_log_repository import CountryLogRepository
from mdm_demo.application.ports.repositories.country_repository import CountryRepository
from mdm_demo.application.ports.repositories.model_log_repository import ModelLogRepository
from mdm_demo.application.ports.repositories.model_repository import ModelRepository
from mdm_demo.infrastructure.persistence.repositories.brand_log_repository import (
    SqlAlchemyBrandLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.brand_repository import (
    SqlAlchemyBrandRepository,
)
from mdm_demo.infrastructure.persistence.repositories.company_log_repository import (
    SqlAlchemyCompanyLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)
from mdm_demo.infrastructure.persistence.repositories.country_log_repository import (
    SqlAlchemyCountryLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.country_repository import (
    SqlAlchemyCountryRepository,
)
from mdm_demo.infrastructure.persistence.repositories.model_log_repository import (
    SqlAlchemyModelLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.model_repository import (
    SqlAlchemyModelRepository,
)


class SqlAlchemyUnitOfWork:
    companies: CompanyRepository
    company_logs: CompanyLogRepository
    models: ModelRepository
    countries: CountryRepository
    model_logs: ModelLogRepository
    country_logs: CountryLogRepository

    brands: BrandRepository
    brand_logs: BrandLogRepository

    def __init__(self, factory: Callable[[], AsyncSession]) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work is already active")
        self._session = self._factory()
        self.companies = SqlAlchemyCompanyRepository(self._session)
        self.company_logs = SqlAlchemyCompanyLogRepository(self._session)
        self.models = SqlAlchemyModelRepository(self._session)
        self.countries = SqlAlchemyCountryRepository(self._session)
        self.model_logs = SqlAlchemyModelLogRepository(self._session)
        self.country_logs = SqlAlchemyCountryLogRepository(self._session)

        self.brands = SqlAlchemyBrandRepository(self._session)
        self.brand_logs = SqlAlchemyBrandLogRepository(self._session)
        return self

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")
        await self._session.commit()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._session
        if session is None:
            return

        async def cleanup() -> None:
            try:
                await session.rollback()
            finally:
                await session.close()

        # Own the cleanup task until completion, even on repeated request cancellation.
        task = asyncio.create_task(cleanup())
        cancelled = False
        try:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    cancelled = True
            task.result()
        finally:
            self._session = None
        if cancelled:
            raise asyncio.CancelledError
