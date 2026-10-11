from typing import Protocol

from mdm_demo.application.ports.repositories.brand_log_repository import BrandLogRepository
from mdm_demo.application.ports.repositories.brand_repository import BrandRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class BrandUnitOfWork(UnitOfWork, Protocol):
    brands: BrandRepository
    brand_logs: BrandLogRepository
