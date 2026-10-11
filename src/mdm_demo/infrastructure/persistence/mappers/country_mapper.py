from mdm_demo.domain.entities.country import Country
from mdm_demo.domain.value_objects.country_code import CountryCode
from mdm_demo.domain.value_objects.country_name import CountryName
from mdm_demo.infrastructure.persistence.models.country import CountryModel


def to_model(country: Country) -> CountryModel:
    return CountryModel(
        id=country.id,
        name=country.name.value,
        code=country.code.value,
        created_at=country.created_at,
        updated_at=country.updated_at,
    )


def to_domain(country: CountryModel) -> Country:
    return Country(
        country.id,
        CountryName(country.name),
        CountryCode(country.code),
        country.created_at,
        country.updated_at,
    )
