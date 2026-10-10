from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.company import CompanyDTO, CompanyPage
from mdm_demo.application.errors import ApplicationError, DuplicateCompanyCode
from mdm_demo.application.ports.cursor import CompanyBoundary, CompanyCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork
from mdm_demo.domain.entities.company import Company
from mdm_demo.domain.entities.company_log import CompanyLog
from mdm_demo.domain.errors import AutoCodeUnavailable, InvalidCompanyValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except InvalidCompanyValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc
    except AutoCodeUnavailable as exc:
        raise ApplicationError("DIMENSION_AUTO_CODE_UNAVAILABLE", "body.code") from exc


class CompanyUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: CompanyCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str | None, request_id: UUID) -> CompanyDTO:
        with translate_domain_errors():
            company = Company.create(name, code)
        try:
            async with self._uow_factory() as uow:
                await uow.companies.add(company)
                await uow.company_logs.add(
                    CompanyLog.record(company.id, "create", request_id, None, company.snapshot())
                )
                await uow.commit()
        except DuplicateCompanyCode as exc:
            error = "DIMENSION_AUTO_CODE_DUPLICATE" if code is None else "COMPANY_CODE_DUPLICATE"
            raise ApplicationError(error, "body.code") from exc
        return CompanyDTO.from_entity(company)

    async def get(self, company_id: UUID) -> CompanyDTO:
        async with self._uow_factory() as uow:
            company = await uow.companies.get(company_id)
            if company is None:
                raise ApplicationError("NOT_FOUND")
            return CompanyDTO.from_entity(company)

    async def rename(self, company_id: UUID, name: str, request_id: UUID) -> CompanyDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                company = await uow.companies.get(company_id, for_update=True)
                if company is None:
                    raise ApplicationError("NOT_FOUND")
                before = company.snapshot()
                if company.rename(name):
                    await uow.companies.save(company)
                    await uow.company_logs.add(
                        CompanyLog.record(
                            company.id, "update", request_id, before, company.snapshot()
                        )
                    )
                    await uow.commit()
                return CompanyDTO.from_entity(company)

    async def delete(self, company_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            company = await uow.companies.get(company_id, for_update=True)
            if company is None:
                raise ApplicationError("NOT_FOUND")
            before = company.snapshot()
            await uow.companies.delete(company)
            await uow.company_logs.add(
                CompanyLog.record(company.id, "delete", request_id, before, None)
            )
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> CompanyPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.companies.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [CompanyDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(CompanyBoundary(last.created_at, last.id))
        return CompanyPage(items, next_cursor, has_next)
