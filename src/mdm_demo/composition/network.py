from fastapi import FastAPI

from mdm_demo.application.use_cases.network import NetworkUseCases
from mdm_demo.application.use_cases.network_log import NetworkLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.network_cursor import SignedNetworkCursor
from mdm_demo.infrastructure.pagination.network_log_cursor import SignedNetworkLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.network import SqlAlchemyNetworkUnitOfWork
from mdm_demo.presentation.routers.network import router
from mdm_demo.presentation.routers.network_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[NetworkUseCases, NetworkLogUseCases]:
    return (
        NetworkUseCases(
            lambda: SqlAlchemyNetworkUnitOfWork(resources.session_factory),
            SignedNetworkCursor(resources.cursor_signing_key),
        ),
        NetworkLogUseCases(
            lambda: SqlAlchemyNetworkUnitOfWork(resources.session_factory),
            SignedNetworkLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.network_use_cases, app.state.network_log_use_cases = build_services(resources)


module = FeatureModule(
    name="network",
    routers=(router, log_router),
    configure=configure,
    state_names=("network_use_cases", "network_log_use_cases"),
)
