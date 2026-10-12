from typing import Protocol

from mdm_demo.application.ports.repositories.category_log_repository import CategoryLogRepository
from mdm_demo.application.ports.repositories.category_repository import CategoryRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class CategoryUnitOfWork(UnitOfWork, Protocol):
    categories: CategoryRepository
    category_logs: CategoryLogRepository


class CategoryLogUnitOfWork(UnitOfWork, Protocol):
    category_logs: CategoryLogRepository
