import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyUnitOfWork(ABC):
    def __init__(self, factory: Callable[[], AsyncSession]) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None

    @abstractmethod
    def _bind_repositories(self, session: AsyncSession) -> None:
        """Bind the repositories of this transaction to its single session."""

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work is already active")
        self._session = self._factory()
        try:
            self._bind_repositories(self._session)
        except BaseException as exc:
            await self.__aexit__(type(exc), exc, exc.__traceback__)
            raise
        return self

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")
        await self._session.commit()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._session
        if session is None:
            return

        async def cleanup() -> None:
            try:
                await session.rollback()
            finally:
                await session.close()

        # Own the cleanup task until completion, even on repeated request cancellation.
        task = asyncio.create_task(cleanup())
        cancelled = False
        try:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    cancelled = True
            task.result()
        finally:
            self._session = None
        if cancelled:
            raise asyncio.CancelledError
