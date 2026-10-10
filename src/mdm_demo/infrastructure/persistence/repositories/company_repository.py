from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors import DuplicateCompanyCode
from mdm_demo.application.ports.cursor import CompanyBoundary
from mdm_demo.domain.entities.company import Company
from mdm_demo.infrastructure.persistence.mappers import company_mapper
from mdm_demo.infrastructure.persistence.models.company import CompanyModel


class SqlAlchemyCompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, company: Company) -> None:
        self._session.add(company_mapper.to_model(company))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            cause = exc.orig.__cause__ if exc.orig is not None else None
            if (
                getattr(cause, "constraint_name", None) == "uq_companies_code"
                and getattr(cause, "sqlstate", None) == "23505"
            ):
                raise DuplicateCompanyCode from exc
            raise

    async def get(self, company_id: UUID, *, for_update: bool = False) -> Company | None:
        statement = select(CompanyModel).where(CompanyModel.id == company_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return company_mapper.to_domain(row) if row is not None else None

    async def save(self, company: Company) -> None:
        await self._session.execute(
            update(CompanyModel)
            .where(CompanyModel.id == company.id)
            .values(name=company.name.value, updated_at=company.updated_at)
        )
        await self._session.flush()

    async def delete(self, company: Company) -> None:
        await self._session.execute(delete(CompanyModel).where(CompanyModel.id == company.id))
        await self._session.flush()

    async def list(self, boundary: CompanyBoundary | None, limit: int) -> list[Company]:
        statement = (
            select(CompanyModel).order_by(CompanyModel.created_at, CompanyModel.id).limit(limit)
        )
        if boundary is not None:
            statement = statement.where(
                tuple_(CompanyModel.created_at, CompanyModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [company_mapper.to_domain(row) for row in rows]
