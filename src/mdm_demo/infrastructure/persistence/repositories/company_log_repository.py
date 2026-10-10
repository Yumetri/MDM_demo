from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursor import CompanyLogBoundary
from mdm_demo.domain.entities.company_log import CompanyLog
from mdm_demo.infrastructure.persistence.mappers.company_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.company_log import CompanyLogModel


class SqlAlchemyCompanyLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: CompanyLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> CompanyLog | None:
        row = await self._session.get(CompanyLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, company_id: UUID, boundary: CompanyLogBoundary | None, limit: int
    ) -> list[CompanyLog]:
        statement = (
            select(CompanyLogModel)
            .where(CompanyLogModel.company_id == company_id)
            .order_by(CompanyLogModel.occurred_at, CompanyLogModel.id)
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CompanyLogModel.occurred_at, CompanyLogModel.id)
                > tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
