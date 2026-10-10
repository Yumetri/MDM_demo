import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from mdm_demo.infrastructure.persistence.models.base import Base
from mdm_demo.infrastructure.persistence.models.company import CompanyModel  # noqa: F401
from mdm_demo.infrastructure.persistence.models.company_log import CompanyLogModel  # noqa: F401
from mdm_demo.infrastructure.persistence.session import database_url


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(database_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(url=database_url(), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    run_migrations(context.config.attributes["connection"])
else:
    asyncio.run(run_online())
