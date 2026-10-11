import os
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.infrastructure.persistence.session import create_session_factory, database_url


def validate_signing_key(key: str) -> None:
    if len(key.encode()) < 32:
        raise ValueError("CURSOR_SIGNING_KEY must contain at least 32 bytes")


@dataclass(frozen=True)
class RuntimeResources:
    session_factory: Callable[[], AsyncSession]
    cursor_signing_key: str

    def __post_init__(self) -> None:
        validate_signing_key(self.cursor_signing_key)


RuntimeFactory = Callable[[], AbstractAsyncContextManager[RuntimeResources]]


@asynccontextmanager
async def production_runtime() -> AsyncGenerator[RuntimeResources]:
    key = os.environ["CURSOR_SIGNING_KEY"]
    validate_signing_key(key)
    engine, factory = create_session_factory(database_url())
    try:
        yield RuntimeResources(factory, key)
    finally:
        await engine.dispose()
