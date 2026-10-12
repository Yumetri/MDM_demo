from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.network import NetworkDTO, NetworkPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.network import DuplicateNetworkCode, DuplicateNetworkName
from mdm_demo.application.ports.cursors.network import NetworkBoundary, NetworkCursor
from mdm_demo.application.ports.units_of_work.network import NetworkUnitOfWork
from mdm_demo.domain.entities.network import Network
from mdm_demo.domain.entities.network_log import NetworkLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.network import InvalidNetworkValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except DuplicateNetworkName as exc:
        raise ApplicationError("NETWORK_NAME_DUPLICATE", "body.name") from exc
    except DuplicateNetworkCode as exc:
        raise ApplicationError("NETWORK_CODE_DUPLICATE", "body.code") from exc
    except AutoCodeUnavailable as exc:
        raise ApplicationError(
            "DIMENSION_AUTO_CODE_UNAVAILABLE", "body.code", dimension="network"
        ) from exc
    except InvalidNetworkValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc


class NetworkUseCases:
    def __init__(self, uow_factory: Callable[[], NetworkUnitOfWork], cursor: NetworkCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str | None, request_id: UUID) -> NetworkDTO:
        with translate_domain_errors():
            network = Network.create(name, code)
        try:
            async with self._uow_factory() as uow:
                await uow.networks.add(network)
                await uow.network_logs.add(
                    NetworkLog.record(network.id, "create", request_id, None, network.snapshot())
                )
                await uow.commit()
        except DuplicateNetworkName as exc:
            raise ApplicationError("NETWORK_NAME_DUPLICATE", "body.name") from exc
        except DuplicateNetworkCode as exc:
            error = "DIMENSION_AUTO_CODE_DUPLICATE" if code is None else "NETWORK_CODE_DUPLICATE"
            raise ApplicationError(error, "body.code") from exc
        return NetworkDTO.from_entity(network)

    async def get(self, network_id: UUID) -> NetworkDTO:
        async with self._uow_factory() as uow:
            network = await uow.networks.get(network_id)
            if network is None:
                raise ApplicationError("NOT_FOUND")
            return NetworkDTO.from_entity(network)

    async def rename(self, network_id: UUID, name: str, request_id: UUID) -> NetworkDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                network = await uow.networks.get(network_id, for_update=True)
                if network is None:
                    raise ApplicationError("NOT_FOUND")
                before = network.snapshot()
                if network.rename(name):
                    await uow.networks.save(network)
                    await uow.network_logs.add(
                        NetworkLog.record(
                            network.id, "update", request_id, before, network.snapshot()
                        )
                    )
                    await uow.commit()
                return NetworkDTO.from_entity(network)

    async def delete(self, network_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            network = await uow.networks.get(network_id, for_update=True)
            if network is None:
                raise ApplicationError("NOT_FOUND")
            before = network.snapshot()
            await uow.networks.delete(network)
            await uow.network_logs.add(
                NetworkLog.record(network.id, "delete", request_id, before, None)
            )
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> NetworkPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.networks.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [NetworkDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(NetworkBoundary(last.created_at, last.id))
        return NetworkPage(items, next_cursor, has_next)
