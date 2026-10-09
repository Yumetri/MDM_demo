"""Application composition root."""

from fastapi import FastAPI
from scalar_fastapi import AgentScalarConfig, add_scalar_reference

from mdm_demo.presentation.routers.health import router as health_router

app = FastAPI(title="MDM API", version="0.1.0", docs_url=None, redoc_url=None)
app.include_router(health_router)
add_scalar_reference(
    app,
    route="/docs",
    scalar_js_url="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.73.1/dist/browser/standalone.js",
    agent=AgentScalarConfig(disabled=True),
    telemetry=False,
)
