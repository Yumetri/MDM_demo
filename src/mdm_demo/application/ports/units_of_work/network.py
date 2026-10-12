from typing import Protocol

from mdm_demo.application.ports.repositories.network_log_repository import NetworkLogRepository
from mdm_demo.application.ports.repositories.network_repository import NetworkRepository
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class NetworkUnitOfWork(UnitOfWork, Protocol):
    networks: NetworkRepository
    network_logs: NetworkLogRepository


class NetworkLogUnitOfWork(UnitOfWork, Protocol):
    network_logs: NetworkLogRepository
