from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.ports.cursors.network import NetworkLogBoundary
from mdm_demo.domain.entities.network_log import NetworkLog
from mdm_demo.infrastructure.persistence.mappers.network_log_mapper import to_domain, to_model
from mdm_demo.infrastructure.persistence.models.network_log import NetworkLogModel


class SqlAlchemyNetworkLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, log: NetworkLog) -> None:
        self._session.add(to_model(log))
        await self._session.flush()

    async def get(self, log_id: UUID) -> NetworkLog | None:
        row = await self._session.get(NetworkLogModel, log_id)
        return to_domain(row) if row is not None else None

    async def list(
        self, network_id: UUID, boundary: NetworkLogBoundary | None, limit: int
    ) -> list[NetworkLog]:
        statement = (
            select(NetworkLogModel)
            .where(NetworkLogModel.network_id == network_id)
            .order_by(NetworkLogModel.occurred_at.desc(), NetworkLogModel.id.desc())
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(NetworkLogModel.occurred_at, NetworkLogModel.id)
                < tuple_(boundary.occurred_at, boundary.id)
            )
        return [to_domain(row) for row in await self._session.scalars(statement)]
