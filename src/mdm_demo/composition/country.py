from fastapi import FastAPI

from mdm_demo.application.use_cases.country import CountryUseCases
from mdm_demo.application.use_cases.country_log import CountryLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.country_cursor import SignedCountryCursor
from mdm_demo.infrastructure.pagination.country_log_cursor import SignedCountryLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.country import SqlAlchemyCountryUnitOfWork
from mdm_demo.presentation.routers.country import router
from mdm_demo.presentation.routers.country_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[CountryUseCases, CountryLogUseCases]:
    return (
        CountryUseCases(
            lambda: SqlAlchemyCountryUnitOfWork(resources.session_factory),
            SignedCountryCursor(resources.cursor_signing_key),
        ),
        CountryLogUseCases(
            lambda: SqlAlchemyCountryUnitOfWork(resources.session_factory),
            SignedCountryLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.country_use_cases, app.state.country_log_use_cases = build_services(resources)


module = FeatureModule(
    name="country",
    routers=(router, log_router),
    configure=configure,
    state_names=("country_use_cases", "country_log_use_cases"),
)
