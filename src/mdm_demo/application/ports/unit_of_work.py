from types import TracebackType
from typing import Protocol, Self

from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.application.ports.repositories.model_log_repository import ModelLogRepository
from mdm_demo.application.ports.repositories.model_repository import ModelRepository


class UnitOfWork(Protocol):
    companies: CompanyRepository
    company_logs: CompanyLogRepository
    models: ModelRepository
    model_logs: ModelLogRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
