from fastapi import FastAPI

from mdm_demo.application.use_cases.category import CategoryUseCases
from mdm_demo.application.use_cases.category_log import CategoryLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.category_cursor import SignedCategoryCursor
from mdm_demo.infrastructure.pagination.category_log_cursor import SignedCategoryLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.category import SqlAlchemyCategoryUnitOfWork
from mdm_demo.presentation.routers.category import router
from mdm_demo.presentation.routers.category_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[CategoryUseCases, CategoryLogUseCases]:
    return (
        CategoryUseCases(
            lambda: SqlAlchemyCategoryUnitOfWork(resources.session_factory),
            SignedCategoryCursor(resources.cursor_signing_key),
        ),
        CategoryLogUseCases(
            lambda: SqlAlchemyCategoryUnitOfWork(resources.session_factory),
            SignedCategoryLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.category_use_cases, app.state.category_log_use_cases = build_services(resources)


module = FeatureModule(
    name="category",
    routers=(router, log_router),
    configure=configure,
    state_names=("category_use_cases", "category_log_use_cases"),
)
