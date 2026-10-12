from typing import cast

from mdm_demo.domain.entities.memory_log import MemoryLog, Operation
from mdm_demo.infrastructure.persistence.models.memory_log import MemoryLogModel


def to_model(log: MemoryLog) -> MemoryLogModel:
    return MemoryLogModel(
        id=log.id,
        memory_id=log.memory_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(model: MemoryLogModel) -> MemoryLog:
    return MemoryLog(
        model.id,
        model.memory_id,
        cast(Operation, model.operation),
        model.occurred_at,
        model.request_id,
        model.before,
        model.after,
    )
