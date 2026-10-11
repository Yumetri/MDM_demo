from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.country import CountryDTO, CountryPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.country import DuplicateCountryCode, DuplicateCountryName
from mdm_demo.application.ports.cursors.country import CountryBoundary, CountryCursor
from mdm_demo.application.ports.units_of_work.country import CountryUnitOfWork
from mdm_demo.domain.entities.country import Country
from mdm_demo.domain.entities.country_log import CountryLog
from mdm_demo.domain.errors.country import InvalidCountryValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except DuplicateCountryName as exc:
        raise ApplicationError("COUNTRY_NAME_DUPLICATE", "body.name") from exc
    except DuplicateCountryCode as exc:
        raise ApplicationError("COUNTRY_CODE_DUPLICATE", "body.code") from exc
    except InvalidCountryValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc


class CountryUseCases:
    def __init__(self, uow_factory: Callable[[], CountryUnitOfWork], cursor: CountryCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str, request_id: UUID) -> CountryDTO:
        with translate_domain_errors():
            country = Country.create(name, code)
            async with self._uow_factory() as uow:
                await uow.countries.add(country)
                await uow.country_logs.add(
                    CountryLog.record(country.id, "create", request_id, None, country.snapshot())
                )
                await uow.commit()
        return CountryDTO.from_entity(country)

    async def get(self, country_id: UUID) -> CountryDTO:
        async with self._uow_factory() as uow:
            country = await uow.countries.get(country_id)
            if country is None:
                raise ApplicationError("NOT_FOUND")
            return CountryDTO.from_entity(country)

    async def rename(self, country_id: UUID, name: str, request_id: UUID) -> CountryDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                country = await uow.countries.get(country_id, for_update=True)
                if country is None:
                    raise ApplicationError("NOT_FOUND")
                before = country.snapshot()
                if country.rename(name):
                    await uow.countries.save(country)
                    await uow.country_logs.add(
                        CountryLog.record(
                            country.id, "update", request_id, before, country.snapshot()
                        )
                    )
                    await uow.commit()
                return CountryDTO.from_entity(country)

    async def delete(self, country_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            country = await uow.countries.get(country_id, for_update=True)
            if country is None:
                raise ApplicationError("NOT_FOUND")
            before = country.snapshot()
            await uow.countries.delete(country)
            await uow.country_logs.add(
                CountryLog.record(country.id, "delete", request_id, before, None)
            )
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> CountryPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.countries.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CountryDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(CountryBoundary(last.created_at, last.id))
        return CountryPage(items, next_cursor, has_next)
