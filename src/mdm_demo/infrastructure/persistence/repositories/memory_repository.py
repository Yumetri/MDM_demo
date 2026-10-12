from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.memory import DuplicateMemoryCapacity
from mdm_demo.application.ports.cursors.memory import MemoryBoundary
from mdm_demo.domain.entities.memory import Memory
from mdm_demo.infrastructure.persistence.mappers import memory_mapper
from mdm_demo.infrastructure.persistence.models.memory import MemoryModel


@contextmanager
def translate_duplicate() -> Generator[None]:
    try:
        yield
    except IntegrityError as exc:
        cause = exc.orig.__cause__ if exc.orig is not None else None
        if (
            getattr(cause, "constraint_name", None)
            in {"uq_memories_capacity_gb", "uq_memories_code"}
            and getattr(cause, "sqlstate", None) == "23505"
        ):
            raise DuplicateMemoryCapacity from exc
        raise


class SqlAlchemyMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, memory: Memory) -> None:
        with translate_duplicate():
            self._session.add(memory_mapper.to_model(memory))
            await self._session.flush()

    async def get(self, memory_id: UUID, *, for_update: bool = False) -> Memory | None:
        statement = select(MemoryModel).where(MemoryModel.id == memory_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return memory_mapper.to_domain(row) if row is not None else None

    async def save(self, memory: Memory) -> None:
        with translate_duplicate():
            await self._session.execute(
                update(MemoryModel)
                .where(MemoryModel.id == memory.id)
                .values(
                    capacity=memory.size.capacity,
                    unit=memory.size.unit,
                    code=memory.size.code,
                    updated_at=memory.updated_at,
                )
            )
            await self._session.flush()

    async def delete(self, memory: Memory) -> None:
        await self._session.execute(delete(MemoryModel).where(MemoryModel.id == memory.id))
        await self._session.flush()

    async def list(self, boundary: MemoryBoundary | None, limit: int) -> list[Memory]:
        statement = (
            select(MemoryModel).order_by(MemoryModel.created_at, MemoryModel.id).limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(MemoryModel.created_at, MemoryModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [memory_mapper.to_domain(row) for row in rows]
