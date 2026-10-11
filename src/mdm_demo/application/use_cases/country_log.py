from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.country_log import CountryLogDTO, CountryLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.country import CountryLogBoundary, CountryLogCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class CountryLogUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: CountryLogCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> CountryLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.country_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return CountryLogDTO.from_entity(log)

    async def list(self, country_id: UUID, cursor: str | None, limit: int) -> CountryLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, country_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.country_logs.list(country_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CountryLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(
                CountryLogBoundary(last.occurred_at, last.id), country_id
            )
        return CountryLogPage(items, next_cursor, has_next)
