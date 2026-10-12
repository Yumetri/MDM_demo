from typing import Protocol

from mdm_demo.application.ports.repositories.memory_log_repository import MemoryLogRepository
from mdm_demo.application.ports.repositories.memory_repository import MemoryRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class MemoryUnitOfWork(UnitOfWork, Protocol):
    memories: MemoryRepository
    memory_logs: MemoryLogRepository


class MemoryLogUnitOfWork(UnitOfWork, Protocol):
    memory_logs: MemoryLogRepository
