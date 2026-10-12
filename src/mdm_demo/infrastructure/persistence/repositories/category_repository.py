from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.category import DuplicateCategoryCode, DuplicateCategoryName
from mdm_demo.application.ports.cursors.category import CategoryBoundary
from mdm_demo.domain.entities.category import Category
from mdm_demo.infrastructure.persistence.mappers import category_mapper
from mdm_demo.infrastructure.persistence.models.category import CategoryModel


class SqlAlchemyCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, category: Category) -> None:
        self._session.add(category_mapper.to_model(category))
        with translate_unique_errors():
            await self._session.flush()

    async def get(self, category_id: UUID, *, for_update: bool = False) -> Category | None:
        statement = select(CategoryModel).where(CategoryModel.id == category_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return category_mapper.to_domain(row) if row is not None else None

    async def save(self, category: Category) -> None:
        with translate_unique_errors():
            await self._session.execute(
                update(CategoryModel)
                .where(CategoryModel.id == category.id)
                .values(name=category.name.value, updated_at=category.updated_at)
            )
            await self._session.flush()

    async def delete(self, category: Category) -> None:
        await self._session.execute(delete(CategoryModel).where(CategoryModel.id == category.id))
        await self._session.flush()

    async def list(self, boundary: CategoryBoundary | None, limit: int) -> list[Category]:
        statement = (
            select(CategoryModel).order_by(CategoryModel.created_at, CategoryModel.id).limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CategoryModel.created_at, CategoryModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [category_mapper.to_domain(row) for row in rows]


@contextmanager
def translate_unique_errors() -> Generator[None]:
    try:
        yield
    except IntegrityError as exc:
        cause = exc.orig.__cause__ if exc.orig is not None else None
        if getattr(cause, "sqlstate", None) == "23505":
            constraint = getattr(cause, "constraint_name", None)
            if constraint == "uq_categories_name":
                raise DuplicateCategoryName from exc
            if constraint == "uq_categories_code":
                raise DuplicateCategoryCode from exc
        raise
