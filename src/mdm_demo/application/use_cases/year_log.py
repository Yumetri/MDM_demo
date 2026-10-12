from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.year_log import YearLogDTO, YearLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.year import YearLogBoundary, YearLogCursor
from mdm_demo.application.ports.units_of_work.year import YearLogUnitOfWork


class YearLogUseCases:
    def __init__(self, uow_factory: Callable[[], YearLogUnitOfWork], cursor: YearLogCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> YearLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.year_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return YearLogDTO.from_entity(log)

    async def list(self, year_id: UUID, cursor: str | None, limit: int) -> YearLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, year_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.year_logs.list(year_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [YearLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(YearLogBoundary(last.occurred_at, last.id), year_id)
        return YearLogPage(items, next_cursor, has_next)
