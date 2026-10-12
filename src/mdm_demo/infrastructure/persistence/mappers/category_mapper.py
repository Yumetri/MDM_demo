from mdm_demo.domain.entities.category import Category
from mdm_demo.domain.value_objects.category_code import CategoryCode
from mdm_demo.domain.value_objects.category_name import CategoryName
from mdm_demo.infrastructure.persistence.models.category import CategoryModel


def to_model(category: Category) -> CategoryModel:
    return CategoryModel(
        id=category.id,
        name=category.name.value,
        code=category.code.value,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def to_domain(category: CategoryModel) -> Category:
    return Category(
        category.id,
        CategoryName(category.name),
        CategoryCode(category.code),
        category.created_at,
        category.updated_at,
    )
