from types import TracebackType
from typing import Protocol, Self

from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.application.ports.repositories.country_log_repository import CountryLogRepository
from mdm_demo.application.ports.repositories.country_repository import CountryRepository
from mdm_demo.application.ports.repositories.model_log_repository import ModelLogRepository
from mdm_demo.application.ports.repositories.model_repository import ModelRepository


class UnitOfWork(Protocol):
    companies: CompanyRepository
    company_logs: CompanyLogRepository
    models: ModelRepository
    countries: CountryRepository
    model_logs: ModelLogRepository
    country_logs: CountryLogRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
