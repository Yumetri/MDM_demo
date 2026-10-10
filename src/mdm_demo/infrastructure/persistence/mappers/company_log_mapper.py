from typing import cast

from mdm_demo.domain.entities.company_log import CompanyLog, Operation
from mdm_demo.infrastructure.persistence.models.company_log import CompanyLogModel


def to_model(log: CompanyLog) -> CompanyLogModel:
    return CompanyLogModel(
        id=log.id,
        company_id=log.company_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(model: CompanyLogModel) -> CompanyLog:
    return CompanyLog(
        model.id,
        model.company_id,
        cast(Operation, model.operation),
        model.occurred_at,
        model.request_id,
        model.before,
        model.after,
    )
