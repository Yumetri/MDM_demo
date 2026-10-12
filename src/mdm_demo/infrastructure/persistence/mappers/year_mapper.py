from mdm_demo.domain.entities.year import Year
from mdm_demo.domain.value_objects.year_code import YearCode
from mdm_demo.domain.value_objects.year_value import YearValue
from mdm_demo.infrastructure.persistence.models.year import YearModel


def to_model(entity: Year) -> YearModel:
    return YearModel(
        id=entity.id,
        year=entity.year.value,
        code=entity.code.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def to_domain(row: YearModel) -> Year:
    return Year(row.id, YearValue(row.year), YearCode(row.code), row.created_at, row.updated_at)
