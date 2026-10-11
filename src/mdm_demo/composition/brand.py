from fastapi import FastAPI

from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.brand_cursor import SignedBrandCursor
from mdm_demo.infrastructure.pagination.brand_log_cursor import SignedBrandLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.brand import SqlAlchemyBrandUnitOfWork
from mdm_demo.presentation.routers.brand import router
from mdm_demo.presentation.routers.brand_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[BrandUseCases, BrandLogUseCases]:
    return (
        BrandUseCases(
            lambda: SqlAlchemyBrandUnitOfWork(resources.session_factory),
            SignedBrandCursor(resources.cursor_signing_key),
        ),
        BrandLogUseCases(
            lambda: SqlAlchemyBrandUnitOfWork(resources.session_factory),
            SignedBrandLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.brand_use_cases, app.state.brand_log_use_cases = build_services(resources)


module = FeatureModule(
    name="brand",
    routers=(router, log_router),
    configure=configure,
    state_names=("brand_use_cases", "brand_log_use_cases"),
)
