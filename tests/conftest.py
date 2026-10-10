import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from mdm_demo.app import create_app
from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor
from mdm_demo.infrastructure.pagination.company_log_cursor import SignedCompanyLogCursor
from mdm_demo.infrastructure.persistence.session import create_session_factory, database_url
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
async def database() -> AsyncIterator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]]]:
    if os.environ.get("POSTGRES_DB") != "mdm_test":
        pytest.fail("Integration/API tests require isolated POSTGRES_DB=mdm_test")
    engine, factory = create_session_factory(database_url())
    try:
        async with engine.begin() as connection:
            await connection.execute(text("TRUNCATE companies, company_logs"))
        yield engine, factory
    finally:
        await engine.dispose()


@pytest.fixture
def cursor_codec() -> SignedCompanyCursor:
    return SignedCompanyCursor("test-only-signing-key-with-at-least-32-bytes")


@pytest.fixture
async def service(database, cursor_codec) -> CompanyUseCases:
    _, factory = database
    return CompanyUseCases(lambda: SqlAlchemyUnitOfWork(factory), cursor_codec)


@pytest.fixture
async def log_service(database) -> CompanyLogUseCases:
    _, factory = database
    return CompanyLogUseCases(
        lambda: SqlAlchemyUnitOfWork(factory),
        SignedCompanyLogCursor("test-only-signing-key-with-at-least-32-bytes"),
    )


@pytest.fixture
async def client(service, log_service) -> AsyncIterator[AsyncClient]:
    app = create_app(service, log_service)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client
