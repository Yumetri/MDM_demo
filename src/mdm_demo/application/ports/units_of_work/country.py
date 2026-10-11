from typing import Protocol

from mdm_demo.application.ports.repositories.country_log_repository import CountryLogRepository
from mdm_demo.application.ports.repositories.country_repository import CountryRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class CountryUnitOfWork(UnitOfWork, Protocol):
    countries: CountryRepository
    country_logs: CountryLogRepository


class CountryLogUnitOfWork(UnitOfWork, Protocol):
    country_logs: CountryLogRepository
