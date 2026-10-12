from typing import cast

from mdm_demo.domain.entities.category_log import CategoryLog, Operation
from mdm_demo.infrastructure.persistence.models.category_log import CategoryLogModel


def to_model(log: CategoryLog) -> CategoryLogModel:
    return CategoryLogModel(
        id=log.id,
        category_id=log.category_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(category: CategoryLogModel) -> CategoryLog:
    return CategoryLog(
        category.id,
        category.category_id,
        cast(Operation, category.operation),
        category.occurred_at,
        category.request_id,
        category.before,
        category.after,
    )
