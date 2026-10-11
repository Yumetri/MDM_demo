from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursor import BrandLogBoundary
from mdm_demo.domain.entities.brand_log import BrandLog
from mdm_demo.infrastructure.persistence.mappers.brand_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.brand_log import BrandLogModel


class SqlAlchemyBrandLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: BrandLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> BrandLog | None:
        row = await self._session.get(BrandLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, brand_id: UUID, boundary: BrandLogBoundary | None, limit: int
    ) -> list[BrandLog]:
        statement = (
            select(BrandLogModel)
            .where(BrandLogModel.brand_id == brand_id)
            .order_by(BrandLogModel.occurred_at, BrandLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(BrandLogModel.occurred_at, BrandLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
