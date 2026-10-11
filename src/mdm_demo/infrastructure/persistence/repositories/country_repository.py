from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.country import DuplicateCountryCode, DuplicateCountryName
from mdm_demo.application.ports.cursors.country import CountryBoundary
from mdm_demo.domain.entities.country import Country
from mdm_demo.infrastructure.persistence.mappers import country_mapper
from mdm_demo.infrastructure.persistence.models.country import CountryModel


class SqlAlchemyCountryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, country: Country) -> None:
        self._session.add(country_mapper.to_model(country))
        with translate_unique_errors():
            await self._session.flush()

    async def get(self, country_id: UUID, *, for_update: bool = False) -> Country | None:
        statement = select(CountryModel).where(CountryModel.id == country_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return country_mapper.to_domain(row) if row is not None else None

    async def save(self, country: Country) -> None:
        with translate_unique_errors():
            await self._session.execute(
                update(CountryModel)
                .where(CountryModel.id == country.id)
                .values(name=country.name.value, updated_at=country.updated_at)
            )
            await self._session.flush()

    async def delete(self, country: Country) -> None:
        await self._session.execute(delete(CountryModel).where(CountryModel.id == country.id))
        await self._session.flush()

    async def list(self, boundary: CountryBoundary | None, limit: int) -> list[Country]:
        statement = (
            select(CountryModel).order_by(CountryModel.created_at, CountryModel.id).limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CountryModel.created_at, CountryModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [country_mapper.to_domain(row) for row in rows]


@contextmanager
def translate_unique_errors() -> Generator[None]:
    try:
        yield
    except IntegrityError as exc:
        cause = exc.orig.__cause__ if exc.orig is not None else None
        if getattr(cause, "sqlstate", None) == "23505":
            constraint = getattr(cause, "constraint_name", None)
            if constraint == "uq_countries_name":
                raise DuplicateCountryName from exc
            if constraint == "uq_countries_code":
                raise DuplicateCountryCode from exc
        raise
