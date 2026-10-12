from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.category import CategoryDTO, CategoryPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.category import DuplicateCategoryCode, DuplicateCategoryName
from mdm_demo.application.ports.cursors.category import CategoryBoundary, CategoryCursor
from mdm_demo.application.ports.units_of_work.category import CategoryUnitOfWork
from mdm_demo.domain.entities.category import Category
from mdm_demo.domain.entities.category_log import CategoryLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.category import InvalidCategoryValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except DuplicateCategoryName as exc:
        raise ApplicationError("CATEGORY_NAME_DUPLICATE", "body.name") from exc
    except DuplicateCategoryCode as exc:
        raise ApplicationError("CATEGORY_CODE_DUPLICATE", "body.code") from exc
    except AutoCodeUnavailable as exc:
        raise ApplicationError(
            "DIMENSION_AUTO_CODE_UNAVAILABLE", "body.code", dimension="category"
        ) from exc
    except InvalidCategoryValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc


class CategoryUseCases:
    def __init__(
        self, uow_factory: Callable[[], CategoryUnitOfWork], cursor: CategoryCursor
    ) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str | None, request_id: UUID) -> CategoryDTO:
        with translate_domain_errors():
            category = Category.create(name, code)
        try:
            async with self._uow_factory() as uow:
                await uow.categories.add(category)
                await uow.category_logs.add(
                    CategoryLog.record(category.id, "create", request_id, None, category.snapshot())
                )
                await uow.commit()
        except DuplicateCategoryName as exc:
            raise ApplicationError("CATEGORY_NAME_DUPLICATE", "body.name") from exc
        except DuplicateCategoryCode as exc:
            error = "DIMENSION_AUTO_CODE_DUPLICATE" if code is None else "CATEGORY_CODE_DUPLICATE"
            raise ApplicationError(error, "body.code") from exc
        return CategoryDTO.from_entity(category)

    async def get(self, category_id: UUID) -> CategoryDTO:
        async with self._uow_factory() as uow:
            category = await uow.categories.get(category_id)
            if category is None:
                raise ApplicationError("NOT_FOUND")
            return CategoryDTO.from_entity(category)

    async def rename(self, category_id: UUID, name: str, request_id: UUID) -> CategoryDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                category = await uow.categories.get(category_id, for_update=True)
                if category is None:
                    raise ApplicationError("NOT_FOUND")
                before = category.snapshot()
                if category.rename(name):
                    await uow.categories.save(category)
                    await uow.category_logs.add(
                        CategoryLog.record(
                            category.id, "update", request_id, before, category.snapshot()
                        )
                    )
                    await uow.commit()
                return CategoryDTO.from_entity(category)

    async def delete(self, category_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            category = await uow.categories.get(category_id, for_update=True)
            if category is None:
                raise ApplicationError("NOT_FOUND")
            before = category.snapshot()
            await uow.categories.delete(category)
            await uow.category_logs.add(
                CategoryLog.record(category.id, "delete", request_id, before, None)
            )
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> CategoryPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.categories.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CategoryDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(CategoryBoundary(last.created_at, last.id))
        return CategoryPage(items, next_cursor, has_next)
