from typing import cast

from mdm_demo.domain.entities.model_log import ModelLog, Operation
from mdm_demo.infrastructure.persistence.models.model_log import ModelLogModel


def to_model(log: ModelLog) -> ModelLogModel:
    return ModelLogModel(
        id=log.id,
        model_id=log.model_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(model: ModelLogModel) -> ModelLog:
    return ModelLog(
        model.id,
        model.model_id,
        cast(Operation, model.operation),
        model.occurred_at,
        model.request_id,
        model.before,
        model.after,
    )
