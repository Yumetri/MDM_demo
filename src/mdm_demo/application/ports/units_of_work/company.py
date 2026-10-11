from typing import Protocol

from mdm_demo.application.ports.repositories.company_log_repository import CompanyLogRepository
from mdm_demo.application.ports.repositories.company_repository import CompanyRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class CompanyUnitOfWork(UnitOfWork, Protocol):
    companies: CompanyRepository
    company_logs: CompanyLogRepository
