from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.network import DuplicateNetworkCode, DuplicateNetworkName
from mdm_demo.application.ports.cursors.network import NetworkBoundary
from mdm_demo.domain.entities.network import Network
from mdm_demo.infrastructure.persistence.mappers import network_mapper
from mdm_demo.infrastructure.persistence.models.network import NetworkModel


class SqlAlchemyNetworkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, network: Network) -> None:
        self._session.add(network_mapper.to_model(network))
        with translate_unique_errors():
            await self._session.flush()

    async def get(self, network_id: UUID, *, for_update: bool = False) -> Network | None:
        statement = select(NetworkModel).where(NetworkModel.id == network_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return network_mapper.to_domain(row) if row is not None else None

    async def save(self, network: Network) -> None:
        with translate_unique_errors():
            await self._session.execute(
                update(NetworkModel)
                .where(NetworkModel.id == network.id)
                .values(name=network.name.value, updated_at=network.updated_at)
            )
            await self._session.flush()

    async def delete(self, network: Network) -> None:
        await self._session.execute(delete(NetworkModel).where(NetworkModel.id == network.id))
        await self._session.flush()

    async def list(self, boundary: NetworkBoundary | None, limit: int) -> list[Network]:
        statement = (
            select(NetworkModel)
            .order_by(NetworkModel.created_at.desc(), NetworkModel.id.desc())
            .limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(NetworkModel.created_at, NetworkModel.id)
                < tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [network_mapper.to_domain(row) for row in rows]


@contextmanager
def translate_unique_errors() -> Generator[None]:
    try:
        yield
    except IntegrityError as exc:
        cause = exc.orig.__cause__ if exc.orig is not None else None
        if getattr(cause, "sqlstate", None) == "23505":
            constraint = getattr(cause, "constraint_name", None)
            if constraint == "uq_networks_name":
                raise DuplicateNetworkName from exc
            if constraint == "uq_networks_code":
                raise DuplicateNetworkCode from exc
        raise
