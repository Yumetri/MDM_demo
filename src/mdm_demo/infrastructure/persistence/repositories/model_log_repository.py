from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursor import ModelLogBoundary
from mdm_demo.domain.entities.model_log import ModelLog
from mdm_demo.infrastructure.persistence.mappers.model_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.model_log import ModelLogModel


class SqlAlchemyModelLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: ModelLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> ModelLog | None:
        row = await self._session.get(ModelLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, model_id: UUID, boundary: ModelLogBoundary | None, limit: int
    ) -> list[ModelLog]:
        statement = (
            select(ModelLogModel)
            .where(ModelLogModel.model_id == model_id)
            .order_by(ModelLogModel.occurred_at, ModelLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(ModelLogModel.occurred_at, ModelLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
