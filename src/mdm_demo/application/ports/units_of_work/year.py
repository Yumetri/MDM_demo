from typing import Protocol

from mdm_demo.application.ports.repositories.year_log_repository import YearLogRepository
from mdm_demo.application.ports.repositories.year_repository import YearRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class YearUnitOfWork(UnitOfWork, Protocol):
    years: YearRepository
    year_logs: YearLogRepository


class YearLogUnitOfWork(UnitOfWork, Protocol):
    year_logs: YearLogRepository
