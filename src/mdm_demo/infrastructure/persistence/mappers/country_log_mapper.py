from typing import cast

from mdm_demo.domain.entities.country_log import CountryLog, Operation
from mdm_demo.infrastructure.persistence.models.country_log import CountryLogModel


def to_model(log: CountryLog) -> CountryLogModel:
    return CountryLogModel(
        id=log.id,
        country_id=log.country_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(country: CountryLogModel) -> CountryLog:
    return CountryLog(
        country.id,
        country.country_id,
        cast(Operation, country.operation),
        country.occurred_at,
        country.request_id,
        country.before,
        country.after,
    )
