"""Application composition root."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from scalar_fastapi import AgentScalarConfig, add_scalar_reference

from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor
from mdm_demo.infrastructure.pagination.company_log_cursor import SignedCompanyLogCursor
from mdm_demo.infrastructure.pagination.model_cursor import SignedModelCursor
from mdm_demo.infrastructure.pagination.model_log_cursor import SignedModelLogCursor
from mdm_demo.infrastructure.persistence.session import create_session_factory, database_url
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from mdm_demo.presentation.exception_handlers import register_exception_handlers
from mdm_demo.presentation.openapi import register_openapi_examples
from mdm_demo.presentation.request_context import RequestContextMiddleware
from mdm_demo.presentation.routers.company import router as company_router
from mdm_demo.presentation.routers.company_log import router as company_log_router
from mdm_demo.presentation.routers.health import router as health_router
from mdm_demo.presentation.routers.model import router as model_router
from mdm_demo.presentation.routers.model_log import router as model_log_router
from mdm_demo.presentation.schemas.examples import WORKFLOW


def create_app(
    service: CompanyUseCases | None = None,
    log_service: CompanyLogUseCases | None = None,
    model_service: ModelUseCases | None = None,
    model_log_service: ModelLogUseCases | None = None,
) -> FastAPI:
    """Build default services, or use a complete set of caller-provided services."""
    services = {
        "service": service,
        "log_service": log_service,
        "model_service": model_service,
        "model_log_service": model_log_service,
    }
    missing = [name for name, value in services.items() if value is None]
    if missing and len(missing) != len(services):
        raise ValueError(
            "Provide all four services or omit all of them. Missing: " + ", ".join(missing)
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        if service is not None:
            app.state.company_use_cases = service
            app.state.company_log_use_cases = log_service
            app.state.model_use_cases = model_service
            app.state.model_log_use_cases = model_log_service
            yield
            return
        cursor = SignedCompanyCursor(os.environ["CURSOR_SIGNING_KEY"])
        engine, factory = create_session_factory(database_url())
        app.state.company_use_cases = CompanyUseCases(lambda: SqlAlchemyUnitOfWork(factory), cursor)
        app.state.company_log_use_cases = CompanyLogUseCases(
            lambda: SqlAlchemyUnitOfWork(factory),
            SignedCompanyLogCursor(os.environ["CURSOR_SIGNING_KEY"]),
        )
        app.state.model_use_cases = ModelUseCases(
            lambda: SqlAlchemyUnitOfWork(factory),
            SignedModelCursor(os.environ["CURSOR_SIGNING_KEY"]),
        )
        app.state.model_log_use_cases = ModelLogUseCases(
            lambda: SqlAlchemyUnitOfWork(factory),
            SignedModelLogCursor(os.environ["CURSOR_SIGNING_KEY"]),
        )
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="MDM API",
        version="0.1.0",
        description=WORKFLOW,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(company_router)
    app.include_router(company_log_router)
    app.include_router(model_router)
    app.include_router(model_log_router)
    register_openapi_examples(app)
    add_scalar_reference(
        app,
        route="/docs",
        scalar_js_url="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.73.1/dist/browser/standalone.js",
        agent=AgentScalarConfig(disabled=True),
        telemetry=False,
    )
    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
