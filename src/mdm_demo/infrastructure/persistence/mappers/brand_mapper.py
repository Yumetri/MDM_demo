from mdm_demo.domain.entities.brand import Brand
from mdm_demo.domain.value_objects.brand_code import BrandCode
from mdm_demo.domain.value_objects.brand_name import BrandName
from mdm_demo.infrastructure.persistence.models.brand import BrandModel


def to_model(brand: Brand) -> BrandModel:
    return BrandModel(
        id=brand.id,
        name=brand.name.value,
        code=brand.code.value,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
    )


def to_domain(brand: BrandModel) -> Brand:
    return Brand(
        brand.id,
        BrandName(brand.name),
        BrandCode(brand.code),
        brand.created_at,
        brand.updated_at,
    )
