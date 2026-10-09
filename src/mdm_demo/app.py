"""Application composition root."""

from fastapi import FastAPI

from mdm_demo.presentation.health import router as health_router

app = FastAPI(title="MDM API", version="0.1.0")
app.include_router(health_router)
