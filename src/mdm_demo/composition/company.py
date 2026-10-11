from fastapi import FastAPI

from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor
from mdm_demo.infrastructure.pagination.company_log_cursor import SignedCompanyLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.company import SqlAlchemyCompanyUnitOfWork
from mdm_demo.presentation.routers.company import router
from mdm_demo.presentation.routers.company_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[CompanyUseCases, CompanyLogUseCases]:
    return (
        CompanyUseCases(
            lambda: SqlAlchemyCompanyUnitOfWork(resources.session_factory),
            SignedCompanyCursor(resources.cursor_signing_key),
        ),
        CompanyLogUseCases(
            lambda: SqlAlchemyCompanyUnitOfWork(resources.session_factory),
            SignedCompanyLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.company_use_cases, app.state.company_log_use_cases = build_services(resources)


module = FeatureModule(
    name="company",
    routers=(router, log_router),
    configure=configure,
    state_names=("company_use_cases", "company_log_use_cases"),
)
