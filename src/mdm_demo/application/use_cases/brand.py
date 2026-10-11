from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.brand import BrandDTO, BrandPage
from mdm_demo.application.errors import ApplicationError, DuplicateBrandCode
from mdm_demo.application.ports.cursor import BrandBoundary, BrandCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork
from mdm_demo.domain.entities.brand import Brand
from mdm_demo.domain.entities.brand_log import BrandLog
from mdm_demo.domain.errors import AutoCodeUnavailable, InvalidBrandValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except InvalidBrandValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc
    except AutoCodeUnavailable as exc:
        raise ApplicationError(
            "DIMENSION_AUTO_CODE_UNAVAILABLE", "body.code", dimension="brand"
        ) from exc


class BrandUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: BrandCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str | None, request_id: UUID) -> BrandDTO:
        with translate_domain_errors():
            brand = Brand.create(name, code)
        try:
            async with self._uow_factory() as uow:
                await uow.brands.add(brand)
                await uow.brand_logs.add(
                    BrandLog.record(brand.id, "create", request_id, None, brand.snapshot())
                )
                await uow.commit()
        except DuplicateBrandCode as exc:
            error = "DIMENSION_AUTO_CODE_DUPLICATE" if code is None else "BRAND_CODE_DUPLICATE"
            raise ApplicationError(error, "body.code") from exc
        return BrandDTO.from_entity(brand)

    async def get(self, brand_id: UUID) -> BrandDTO:
        async with self._uow_factory() as uow:
            brand = await uow.brands.get(brand_id)
            if brand is None:
                raise ApplicationError("NOT_FOUND")
            return BrandDTO.from_entity(brand)

    async def rename(self, brand_id: UUID, name: str, request_id: UUID) -> BrandDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                brand = await uow.brands.get(brand_id, for_update=True)
                if brand is None:
                    raise ApplicationError("NOT_FOUND")
                before = brand.snapshot()
                if brand.rename(name):
                    await uow.brands.save(brand)
                    await uow.brand_logs.add(
                        BrandLog.record(brand.id, "update", request_id, before, brand.snapshot())
                    )
                    await uow.commit()
                return BrandDTO.from_entity(brand)

    async def delete(self, brand_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            brand = await uow.brands.get(brand_id, for_update=True)
            if brand is None:
                raise ApplicationError("NOT_FOUND")
            before = brand.snapshot()
            await uow.brands.delete(brand)
            await uow.brand_logs.add(BrandLog.record(brand.id, "delete", request_id, before, None))
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> BrandPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.brands.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [BrandDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(BrandBoundary(last.created_at, last.id))
        return BrandPage(items, next_cursor, has_next)
