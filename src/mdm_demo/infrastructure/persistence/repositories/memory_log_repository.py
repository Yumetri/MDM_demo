from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursors.memory import MemoryLogBoundary
from mdm_demo.domain.entities.memory_log import MemoryLog
from mdm_demo.infrastructure.persistence.mappers.memory_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.memory_log import MemoryLogModel


class SqlAlchemyMemoryLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: MemoryLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> MemoryLog | None:
        row = await self._session.get(MemoryLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, memory_id: UUID, boundary: MemoryLogBoundary | None, limit: int
    ) -> list[MemoryLog]:
        statement = (
            select(MemoryLogModel)
            .where(MemoryLogModel.memory_id == memory_id)
            .order_by(MemoryLogModel.occurred_at, MemoryLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(MemoryLogModel.occurred_at, MemoryLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
