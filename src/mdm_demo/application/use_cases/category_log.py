from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.category_log import CategoryLogDTO, CategoryLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.category import CategoryLogBoundary, CategoryLogCursor
from mdm_demo.application.ports.units_of_work.category import CategoryLogUnitOfWork


class CategoryLogUseCases:
    def __init__(
        self, uow_factory: Callable[[], CategoryLogUnitOfWork], cursor: CategoryLogCursor
    ) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> CategoryLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.category_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return CategoryLogDTO.from_entity(log)

    async def list(self, category_id: UUID, cursor: str | None, limit: int) -> CategoryLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, category_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.category_logs.list(category_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CategoryLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(
                CategoryLogBoundary(last.occurred_at, last.id), category_id
            )
        return CategoryLogPage(items, next_cursor, has_next)
