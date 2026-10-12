import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from mdm_demo.app import create_app
from mdm_demo.composition.runtime import RuntimeResources
from mdm_demo.infrastructure.persistence.models.base import Base
from mdm_demo.infrastructure.persistence.session import create_session_factory, database_url

pytest_plugins = (
    "tests.fixtures.company",
    "tests.fixtures.model",
    "tests.fixtures.country",
    "tests.fixtures.brand",
    "tests.fixtures.year",
)


@pytest.fixture
def signing_key() -> str:
    return "test-only-signing-key-with-at-least-32-bytes"


@pytest.fixture
async def database() -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    if os.environ.get("POSTGRES_DB") != "mdm_test":
        pytest.fail("Integration/API tests require isolated POSTGRES_DB=mdm_test")
    engine, factory = create_session_factory(database_url())
    try:
        async with engine.begin() as connection:
            # Only application-owned tables; migration history is not part of Base metadata.
            tables = ", ".join(
                connection.dialect.identifier_preparer.format_table(table)
                for table in Base.metadata.sorted_tables
            )
            if tables:
                await connection.execute(text(f"TRUNCATE {tables}"))
        yield engine, factory
    finally:
        await engine.dispose()


@pytest.fixture
def runtime_resources(database, signing_key) -> RuntimeResources:
    return RuntimeResources(database[1], signing_key)


@pytest.fixture
def app_factory(runtime_resources):
    @asynccontextmanager
    async def borrowed_runtime() -> AsyncGenerator[RuntimeResources]:
        # The database fixture owns the engine, not this application's lifespan.
        yield runtime_resources

    def build(*, modules=None):
        return create_app(modules=modules, runtime_factory=borrowed_runtime)

    return build


@pytest.fixture
async def client(app_factory) -> AsyncGenerator[AsyncClient]:
    app = app_factory()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client
