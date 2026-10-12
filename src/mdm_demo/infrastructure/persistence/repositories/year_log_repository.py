from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursors.year import YearLogBoundary
from mdm_demo.domain.entities.year_log import YearLog
from mdm_demo.infrastructure.persistence.mappers.year_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.year_log import YearLogModel


class SqlAlchemyYearLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: YearLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> YearLog | None:
        row = await self._session.get(YearLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, year_id: UUID, boundary: YearLogBoundary | None, limit: int
    ) -> list[YearLog]:
        statement = (
            select(YearLogModel)
            .where(YearLogModel.year_id == year_id)
            .order_by(YearLogModel.occurred_at.desc(), YearLogModel.id.desc())
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(YearLogModel.occurred_at, YearLogModel.id)
                < tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
