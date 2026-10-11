from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors import DuplicateBrandCode
from mdm_demo.application.ports.cursor import BrandBoundary
from mdm_demo.domain.entities.brand import Brand
from mdm_demo.infrastructure.persistence.mappers import brand_mapper
from mdm_demo.infrastructure.persistence.models.brand import BrandModel


class SqlAlchemyBrandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, brand: Brand) -> None:
        self._session.add(brand_mapper.to_model(brand))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            cause = exc.orig.__cause__ if exc.orig is not None else None
            if (
                getattr(cause, "constraint_name", None) == "uq_brands_code"
                and getattr(cause, "sqlstate", None) == "23505"
            ):
                raise DuplicateBrandCode from exc
            raise

    async def get(self, brand_id: UUID, *, for_update: bool = False) -> Brand | None:
        statement = select(BrandModel).where(BrandModel.id == brand_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return brand_mapper.to_domain(row) if row is not None else None

    async def save(self, brand: Brand) -> None:
        await self._session.execute(
            update(BrandModel)
            .where(BrandModel.id == brand.id)
            .values(name=brand.name.value, updated_at=brand.updated_at)
        )
        await self._session.flush()

    async def delete(self, brand: Brand) -> None:
        await self._session.execute(delete(BrandModel).where(BrandModel.id == brand.id))
        await self._session.flush()

    async def list(self, boundary: BrandBoundary | None, limit: int) -> list[Brand]:
        statement = select(BrandModel).order_by(BrandModel.created_at, BrandModel.id).limit(limit)
        if boundary is not None:
            statement = statement.where(
                tuple_(BrandModel.created_at, BrandModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [brand_mapper.to_domain(row) for row in rows]
