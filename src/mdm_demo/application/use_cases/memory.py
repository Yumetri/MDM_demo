from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.memory import MemoryDTO, MemoryPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.memory import DuplicateMemoryCapacity
from mdm_demo.application.ports.cursors.memory import MemoryBoundary, MemoryCursor
from mdm_demo.application.ports.units_of_work.memory import MemoryUnitOfWork
from mdm_demo.domain.entities.memory import Memory
from mdm_demo.domain.entities.memory_log import MemoryLog
from mdm_demo.domain.errors.memory import InvalidMemoryValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except InvalidMemoryValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc


class MemoryUseCases:
    def __init__(self, uow_factory: Callable[[], MemoryUnitOfWork], cursor: MemoryCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, capacity: int, unit: str, request_id: UUID) -> MemoryDTO:
        with translate_domain_errors():
            memory = Memory.create(capacity, unit)
        try:
            async with self._uow_factory() as uow:
                await uow.memories.add(memory)
                await uow.memory_logs.add(
                    MemoryLog.record(memory.id, "create", request_id, None, memory.snapshot())
                )
                await uow.commit()
        except DuplicateMemoryCapacity as exc:
            raise ApplicationError("MEMORY_CAPACITY_DUPLICATE", "body.capacity") from exc
        return MemoryDTO.from_entity(memory)

    async def get(self, memory_id: UUID) -> MemoryDTO:
        async with self._uow_factory() as uow:
            memory = await uow.memories.get(memory_id)
            if memory is None:
                raise ApplicationError("NOT_FOUND")
            return MemoryDTO.from_entity(memory)

    async def change_size(
        self, memory_id: UUID, capacity: int, unit: str, request_id: UUID
    ) -> MemoryDTO:
        try:
            with translate_domain_errors():
                async with self._uow_factory() as uow:
                    memory = await uow.memories.get(memory_id, for_update=True)
                    if memory is None:
                        raise ApplicationError("NOT_FOUND")
                    before = memory.snapshot()
                    if memory.change_size(capacity, unit):
                        await uow.memories.save(memory)
                        await uow.memory_logs.add(
                            MemoryLog.record(
                                memory.id, "update", request_id, before, memory.snapshot()
                            )
                        )
                        await uow.commit()
                    return MemoryDTO.from_entity(memory)
        except DuplicateMemoryCapacity as exc:
            raise ApplicationError("MEMORY_CAPACITY_DUPLICATE", "body.capacity") from exc

    async def delete(self, memory_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            memory = await uow.memories.get(memory_id, for_update=True)
            if memory is None:
                raise ApplicationError("NOT_FOUND")
            before = memory.snapshot()
            await uow.memories.delete(memory)
            await uow.memory_logs.add(
                MemoryLog.record(memory.id, "delete", request_id, before, None)
            )
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> MemoryPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.memories.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [MemoryDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(MemoryBoundary(last.created_at, last.id))
        return MemoryPage(items, next_cursor, has_next)
