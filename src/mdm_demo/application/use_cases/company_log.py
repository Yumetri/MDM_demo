from collections.abc import Callable
from uuid import UUID

from mdm_demo.application.dto.company_log import CompanyLogDTO, CompanyLogPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursor import CompanyLogBoundary, CompanyLogCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork


class CompanyLogUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: CompanyLogCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def get(self, log_id: UUID) -> CompanyLogDTO:
        async with self._uow_factory() as uow:
            log = await uow.company_logs.get(log_id)
            if log is None:
                raise ApplicationError("NOT_FOUND")
            return CompanyLogDTO.from_entity(log)

    async def list(self, company_id: UUID, cursor: str | None, limit: int) -> CompanyLogPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor, company_id) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.company_logs.list(company_id, boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CompanyLogDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(
                CompanyLogBoundary(last.occurred_at, last.id), company_id
            )
        return CompanyLogPage(items, next_cursor, has_next)
