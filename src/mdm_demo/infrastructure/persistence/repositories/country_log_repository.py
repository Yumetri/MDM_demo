from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursors.country import CountryLogBoundary
from mdm_demo.domain.entities.country_log import CountryLog
from mdm_demo.infrastructure.persistence.mappers.country_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.country_log import CountryLogModel


class SqlAlchemyCountryLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: CountryLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> CountryLog | None:
        row = await self._session.get(CountryLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, country_id: UUID, boundary: CountryLogBoundary | None, limit: int
    ) -> list[CountryLog]:
        statement = (
            select(CountryLogModel)
            .where(CountryLogModel.country_id == country_id)
            .order_by(CountryLogModel.occurred_at, CountryLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CountryLogModel.occurred_at, CountryLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
