from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.brand_log import BrandLogDTO, BrandLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.brand import BrandLogBoundary, BrandLogCursor
from mdm_demo.application.ports.units_of_work.brand import BrandUnitOfWork


class BrandLogUseCases:
    def __init__(self, uow_factory: Callable[[], BrandUnitOfWork], cursor: BrandLogCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> BrandLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.brand_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return BrandLogDTO.from_entity(log)

    async def list(self, brand_id: UUID, cursor: str | None, limit: int) -> BrandLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, brand_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.brand_logs.list(brand_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [BrandLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(BrandLogBoundary(last.occurred_at, last.id), brand_id)
        return BrandLogPage(items, next_cursor, has_next)
