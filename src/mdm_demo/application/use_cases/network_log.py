from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.network_log import NetworkLogDTO, NetworkLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.network import NetworkLogBoundary, NetworkLogCursor
from mdm_demo.application.ports.units_of_work.network import NetworkLogUnitOfWork


class NetworkLogUseCases:
    def __init__(
        self, uow_factory: Callable[[], NetworkLogUnitOfWork], cursor: NetworkLogCursor
    ) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> NetworkLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.network_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return NetworkLogDTO.from_entity(log)

    async def list(self, network_id: UUID, cursor: str | None, limit: int) -> NetworkLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, network_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.network_logs.list(network_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [NetworkLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(
                NetworkLogBoundary(last.occurred_at, last.id), network_id
            )
        return NetworkLogPage(items, next_cursor, has_next)
