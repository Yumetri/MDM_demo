from typing import Protocol

from mdm_demo.application.ports.repositories.model_log_repository import ModelLogRepository
from mdm_demo.application.ports.repositories.model_repository import ModelRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class ModelUnitOfWork(UnitOfWork, Protocol):
    models: ModelRepository
    model_logs: ModelLogRepository
