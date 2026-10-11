from fastapi import FastAPI

from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.model_cursor import SignedModelCursor
from mdm_demo.infrastructure.pagination.model_log_cursor import SignedModelLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.model import SqlAlchemyModelUnitOfWork
from mdm_demo.presentation.routers.model import router
from mdm_demo.presentation.routers.model_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[ModelUseCases, ModelLogUseCases]:
    return (
        ModelUseCases(
            lambda: SqlAlchemyModelUnitOfWork(resources.session_factory),
            SignedModelCursor(resources.cursor_signing_key),
        ),
        ModelLogUseCases(
            lambda: SqlAlchemyModelUnitOfWork(resources.session_factory),
            SignedModelLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.model_use_cases, app.state.model_log_use_cases = build_services(resources)


module = FeatureModule(
    name="model",
    routers=(router, log_router),
    configure=configure,
    state_names=("model_use_cases", "model_log_use_cases"),
)
