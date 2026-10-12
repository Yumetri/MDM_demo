from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursors.category import CategoryLogBoundary
from mdm_demo.domain.entities.category_log import CategoryLog
from mdm_demo.infrastructure.persistence.mappers.category_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.category_log import CategoryLogModel


class SqlAlchemyCategoryLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: CategoryLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> CategoryLog | None:
        row = await self._session.get(CategoryLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, category_id: UUID, boundary: CategoryLogBoundary | None, limit: int
    ) -> list[CategoryLog]:
        statement = (
            select(CategoryLogModel)
            .where(CategoryLogModel.category_id == category_id)
            .order_by(CategoryLogModel.occurred_at, CategoryLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CategoryLogModel.occurred_at, CategoryLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
