"""FastAPI setup; explicit feature composition owns concrete dependencies."""

import logging
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from scalar_fastapi import AgentScalarConfig, add_scalar_reference

from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.registry import DEFAULT_MODULES
from mdm_demo.composition.routes import validate_http_routes
from mdm_demo.composition.runtime import RuntimeFactory, production_runtime
from mdm_demo.presentation.exception_handlers import register_exception_handlers
from mdm_demo.presentation.openapi import register_openapi_examples
from mdm_demo.presentation.request_context import RequestContextMiddleware
from mdm_demo.presentation.routers.health import router as health_router
from mdm_demo.presentation.schemas.examples import WORKFLOW


def create_app(
    *,
    modules: Sequence[FeatureModule] | None = None,
    runtime_factory: RuntimeFactory = production_runtime,
) -> FastAPI:
    selected = tuple(DEFAULT_MODULES if modules is None else modules)
    names: set[str] = set()
    state_names: set[str] = set()
    for module in selected:
        if not module.name or module.name in names:
            raise ValueError(f"Duplicate or empty feature name: {module.name}")
        names.add(module.name)
        for name in module.state_names:
            if not name or name in state_names:
                raise ValueError(f"Duplicate or empty service state: {name}")
            state_names.add(name)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        try:
            async with runtime_factory() as resources:
                for module in selected:
                    module.configure(app, resources)
                    missing = [
                        name
                        for name in module.state_names
                        if getattr(app.state, name, None) is None
                    ]
                    if missing:
                        raise ValueError(
                            f"Feature {module.name} did not configure services: {missing}"
                        )
                yield
        finally:
            for name in state_names:
                if hasattr(app.state, name):
                    delattr(app.state, name)

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
    for module in selected:
        for router in module.routers:
            app.include_router(router)
    register_openapi_examples(app)
    add_scalar_reference(
        app,
        route="/docs",
        scalar_js_url="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.73.1/dist/browser/standalone.js",
        agent=AgentScalarConfig(disabled=True),
        telemetry=False,
    )
    validate_http_routes(app.routes, reserved_paths={"/docs", "/openapi.json", "/health"})
    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
