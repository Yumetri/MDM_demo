from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.model_log import ModelLogDTO, ModelLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.model import ModelLogBoundary, ModelLogCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class ModelLogUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: ModelLogCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> ModelLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.model_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return ModelLogDTO.from_entity(log)

    async def list(self, model_id: UUID, cursor: str | None, limit: int) -> ModelLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, model_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.model_logs.list(model_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [ModelLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(ModelLogBoundary(last.occurred_at, last.id), model_id)
        return ModelLogPage(items, next_cursor, has_next)
