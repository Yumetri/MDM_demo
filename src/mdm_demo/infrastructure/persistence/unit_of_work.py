import asyncio
from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.infrastructure.persistence.repositories.company_log_repository import (
    SqlAlchemyCompanyLogRepository,
)
from mdm_demo.infrastructure.persistence.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
)


class SqlAlchemyUnitOfWork:
    companies: CompanyRepository
    company_logs: CompanyLogRepository

    def __init__(self, factory: Callable[[], AsyncSession]) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work is already active")
        self._session = self._factory()
        self.companies = SqlAlchemyCompanyRepository(self._session)
        self.company_logs = SqlAlchemyCompanyLogRepository(self._session)
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
