from fastapi import FastAPI

from mdm_demo.application.use_cases.memory import MemoryUseCases
from mdm_demo.application.use_cases.memory_log import MemoryLogUseCases
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.pagination.memory_cursor import SignedMemoryCursor
from mdm_demo.infrastructure.pagination.memory_log_cursor import SignedMemoryLogCursor
from mdm_demo.infrastructure.persistence.units_of_work.memory import SqlAlchemyMemoryUnitOfWork
from mdm_demo.presentation.routers.memory import router
from mdm_demo.presentation.routers.memory_log import router as log_router


def build_services(resources: RuntimeResources) -> tuple[MemoryUseCases, MemoryLogUseCases]:
    return (
        MemoryUseCases(
            lambda: SqlAlchemyMemoryUnitOfWork(resources.session_factory),
            SignedMemoryCursor(resources.cursor_signing_key),
        ),
        MemoryLogUseCases(
            lambda: SqlAlchemyMemoryUnitOfWork(resources.session_factory),
            SignedMemoryLogCursor(resources.cursor_signing_key),
        ),
    )


def configure(app: FastAPI, resources: RuntimeResources) -> None:
    app.state.memory_use_cases, app.state.memory_log_use_cases = build_services(resources)


module = FeatureModule(
    name="memory",
    routers=(router, log_router),
    configure=configure,
    state_names=("memory_use_cases", "memory_log_use_cases"),
)
