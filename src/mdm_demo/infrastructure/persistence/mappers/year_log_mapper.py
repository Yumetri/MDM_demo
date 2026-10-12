from typing import cast

from mdm_demo.domain.entities.year_log import Operation, YearLog
from mdm_demo.infrastructure.persistence.models.year_log import YearLogModel


def to_model(log: YearLog) -> YearLogModel:
    return YearLogModel(
        id=log.id,
        year_id=log.year_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(year: YearLogModel) -> YearLog:
    return YearLog(
        year.id,
        year.year_id,
        cast(Operation, year.operation),
        year.occurred_at,
        year.request_id,
        year.before,
        year.after,
    )
