from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.year import YearDTO, YearPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.year import DuplicateYear
from mdm_demo.application.ports.cursors.year import YearBoundary, YearCursor
from mdm_demo.application.ports.units_of_work.year import YearUnitOfWork
from mdm_demo.domain.entities.year import Year
from mdm_demo.domain.entities.year_log import YearLog
from mdm_demo.domain.errors.year import InvalidYearValue


@contextmanager
def translate_errors() -> Generator[None]:
    try:
        yield
    except InvalidYearValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc
    except DuplicateYear as exc:
        raise ApplicationError("YEAR_DUPLICATE", "body.year") from exc


class YearUseCases:
    def __init__(self, uow_factory: Callable[[], YearUnitOfWork], cursor: YearCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, year: int, request_id: UUID) -> YearDTO:
        with translate_errors():
            entity = Year.create(year)
            async with self._uow_factory() as uow:
                await uow.years.add(entity)
                await uow.year_logs.add(
                    YearLog.record(entity.id, "create", request_id, None, entity.snapshot())
                )
                await uow.commit()
        return YearDTO.from_entity(entity)

    async def get(self, year_id: UUID) -> YearDTO:
        async with self._uow_factory() as uow:
            entity = await uow.years.get(year_id)
            if entity is None:
                raise ApplicationError("NOT_FOUND")
            return YearDTO.from_entity(entity)

    async def change_year(self, year_id: UUID, year: int, request_id: UUID) -> YearDTO:
        with translate_errors():
            async with self._uow_factory() as uow:
                entity = await uow.years.get(year_id, for_update=True)
                if entity is None:
                    raise ApplicationError("NOT_FOUND")
                before = entity.snapshot()
                if entity.change_year(year):
                    await uow.years.save(entity)
                    await uow.year_logs.add(
                        YearLog.record(entity.id, "update", request_id, before, entity.snapshot())
                    )
                    await uow.commit()
                return YearDTO.from_entity(entity)

    async def delete(self, year_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            entity = await uow.years.get(year_id, for_update=True)
            if entity is None:
                raise ApplicationError("NOT_FOUND")
            before = entity.snapshot()
            await uow.years.delete(entity)
            await uow.year_logs.add(YearLog.record(entity.id, "delete", request_id, before, None))
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> YearPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.years.list(boundary, limit + 1)
        items = [YearDTO.from_entity(row) for row in rows[:limit]]
        has_next = len(rows) > limit
        next_cursor = self._cursor.encode(YearBoundary(items[-1].year)) if has_next else None
        return YearPage(items, next_cursor, has_next)
