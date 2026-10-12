from fastapi import FastAPI

from mdm_demo.application.use_cases.year import YearUseCases
from mdm_demo.application.use_cases.year_log import YearLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.year_cursor import SignedYearCursor
from mdm_demo.infrastructure.pagination.year_log_cursor import SignedYearLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.year import SqlAlchemyYearUnitOfWork
from mdm_demo.presentation.routers.year import router
from mdm_demo.presentation.routers.year_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[YearUseCases, YearLogUseCases]:
    return (
        YearUseCases(
            lambda: SqlAlchemyYearUnitOfWork(resources.session_factory),
            SignedYearCursor(resources.cursor_signing_key),
        ),
        YearLogUseCases(
            lambda: SqlAlchemyYearUnitOfWork(resources.session_factory),
            SignedYearLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.year_use_cases, app.state.year_log_use_cases = build_services(resources)


module = FeatureModule(
    name="year",
    routers=(router, log_router),
    configure=configure,
    state_names=("year_use_cases", "year_log_use_cases"),
)
