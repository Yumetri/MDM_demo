from mdm_demo.domain.entities.company import Company
from mdm_demo.domain.value_objects.company_code import CompanyCode
from mdm_demo.domain.value_objects.company_name import CompanyName
from mdm_demo.infrastructure.persistence.models.company import CompanyModel


def to_model(company: Company) -> CompanyModel:
    return CompanyModel(
        id=company.id,
        name=company.name.value,
        code=company.code.value,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def to_domain(model: CompanyModel) -> Company:
    return Company(
        model.id,
        CompanyName(model.name),
        CompanyCode(model.code),
        model.created_at,
        model.updated_at,
    )
