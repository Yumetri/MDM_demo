from uuid import UUID

from sqlalchemy import delete, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.application.errors.model import DuplicateModelCode
from mdm_demo.application.ports.cursors.model import ModelBoundary
from mdm_demo.domain.entities.model import Model
from mdm_demo.infrastructure.persistence.mappers import model_mapper
from mdm_demo.infrastructure.persistence.models.model import ModelModel


class SqlAlchemyModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, model: Model) -> None:
        self._session.add(model_mapper.to_model(model))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            cause = exc.orig.__cause__ if exc.orig is not None else None
            if (
                getattr(cause, "constraint_name", None) == "uq_models_code"
                and getattr(cause, "sqlstate", None) == "23505"
            ):
                raise DuplicateModelCode from exc
            raise

    async def get(self, model_id: UUID, *, for_update: bool = False) -> Model | None:
        statement = select(ModelModel).where(ModelModel.id == model_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return model_mapper.to_domain(row) if row is not None else None

    async def save(self, model: Model) -> None:
        await self._session.execute(
            update(ModelModel)
            .where(ModelModel.id == model.id)
            .values(name=model.name.value, updated_at=model.updated_at)
        )
        await self._session.flush()

    async def delete(self, model: Model) -> None:
        await self._session.execute(delete(ModelModel).where(ModelModel.id == model.id))
        await self._session.flush()

    async def list(self, boundary: ModelBoundary | None, limit: int) -> list[Model]:
        statement = select(ModelModel).order_by(ModelModel.created_at, ModelModel.id).limit(limit)
        if boundary is not None:
            statement = statement.where(
                tuple_(ModelModel.created_at, ModelModel.id)
                > tuple_(boundary.created_at, boundary.id)
            )
        rows = await self._session.scalars(statement)
        return [model_mapper.to_domain(row) for row in rows]
