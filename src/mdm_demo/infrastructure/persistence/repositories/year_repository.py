from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.year import DuplicateYear
from mdm_demo.application.ports.cursors.year import YearBoundary
from mdm_demo.domain.entities.year import Year
from mdm_demo.infrastructure.persistence.mappers import year_mapper
from mdm_demo.infrastructure.persistence.models.year import YearModel


class SqlAlchemyYearRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, year: Year) -> None:
        self._session.add(year_mapper.to_model(year))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            cause = exc.orig.__cause__ if exc.orig is not None else None
            if (
                getattr(cause, "constraint_name", None) in {"uq_years_year", "uq_years_code"}
                and getattr(cause, "sqlstate", None) == "23505"
            ):
                raise DuplicateYear from exc
            raise

    async def get(self, year_id: UUID, *, for_update: bool = False) -> Year | None:
        statement = select(YearModel).where(YearModel.id == year_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return year_mapper.to_domain(row) if row is not None else None

    async def save(self, year: Year) -> None:
        try:
            await self._session.execute(
                update(YearModel)
                .where(YearModel.id == year.id)
                .values(year=year.year.value, code=year.code.value, updated_at=year.updated_at)
            )
            await self._session.flush()
        except IntegrityError as exc:
            cause = exc.orig.__cause__ if exc.orig is not None else None
            if (
                getattr(cause, "constraint_name", None) in {"uq_years_year", "uq_years_code"}
                and getattr(cause, "sqlstate", None) == "23505"
            ):
                raise DuplicateYear from exc
            raise

    async def delete(self, year: Year) -> None:
        await self._session.execute(delete(YearModel).where(YearModel.id == year.id))
        await self._session.flush()

    async def list(self, boundary: YearBoundary | None, limit: int) -> list[Year]:
        statement = select(YearModel).order_by(YearModel.year.desc()).limit(limit)
        if boundary is not None:
            statement = statement.where(YearModel.year < boundary.year)
        return [year_mapper.to_domain(row) for row in await self._session.scalars(statement)]
