from typing import cast

from mdm_demo.domain.entities.brand_log import BrandLog, Operation
from mdm_demo.infrastructure.persistence.models.brand_log import BrandLogModel


def to_model(log: BrandLog) -> BrandLogModel:
    return BrandLogModel(
        id=log.id,
        brand_id=log.brand_id,
        operation=log.operation,
        occurred_at=log.occurred_at,
        request_id=log.request_id,
        before=dict(log.before) if log.before is not None else None,
        after=dict(log.after) if log.after is not None else None,
    )


def to_domain(brand: BrandLogModel) -> BrandLog:
    return BrandLog(
        brand.id,
        brand.brand_id,
        cast(Operation, brand.operation),
        brand.occurred_at,
        brand.request_id,
        brand.before,
        brand.after,
    )
