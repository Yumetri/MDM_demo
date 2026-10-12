from typing import cast

from mdm_demo.domain.entities.network_log import NetworkLog, Operation
from mdm_demo.infrastructure.persistence.models.network_log import NetworkLogModel


def to_model(log: NetworkLog) -> NetworkLogModel:
    return NetworkLogModel(
        id=log.id,
        network_id=log.network_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(network: NetworkLogModel) -> NetworkLog:
    return NetworkLog(
        network.id,
        network.network_id,
        cast(Operation, network.operation),
        network.occurred_at,
        network.request_id,
        network.before,
        network.after,
    )
