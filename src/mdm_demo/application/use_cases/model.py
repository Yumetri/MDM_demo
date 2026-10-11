from collections.abc import Callable, Generator
from contextlib import contextmanager
from uuid import UUID

from mdm_demo.application.dto.model import ModelDTO, ModelPage
from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.model import DuplicateModelCode
from mdm_demo.application.ports.cursors.model import ModelBoundary, ModelCursor
from mdm_demo.application.ports.unit_of_work import UnitOfWork
from mdm_demo.domain.entities.model import Model
from mdm_demo.domain.entities.model_log import ModelLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.model import InvalidModelValue


@contextmanager
def translate_domain_errors() -> Generator[None]:
    try:
        yield
    except InvalidModelValue as exc:
        raise ApplicationError("VALIDATION_ERROR", f"body.{exc.field}") from exc
    except AutoCodeUnavailable as exc:
        raise ApplicationError(
            "DIMENSION_AUTO_CODE_UNAVAILABLE", "body.code", dimension="model"
        ) from exc


class ModelUseCases:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], cursor: ModelCursor) -> None:
        self._uow_factory = uow_factory
        self._cursor = cursor

    async def create(self, name: str, code: str | None, request_id: UUID) -> ModelDTO:
        with translate_domain_errors():
            model = Model.create(name, code)
        try:
            async with self._uow_factory() as uow:
                await uow.models.add(model)
                await uow.model_logs.add(
                    ModelLog.record(model.id, "create", request_id, None, model.snapshot())
                )
                await uow.commit()
        except DuplicateModelCode as exc:
            error = "DIMENSION_AUTO_CODE_DUPLICATE" if code is None else "MODEL_CODE_DUPLICATE"
            raise ApplicationError(error, "body.code") from exc
        return ModelDTO.from_entity(model)

    async def get(self, model_id: UUID) -> ModelDTO:
        async with self._uow_factory() as uow:
            model = await uow.models.get(model_id)
            if model is None:
                raise ApplicationError("NOT_FOUND")
            return ModelDTO.from_entity(model)

    async def rename(self, model_id: UUID, name: str, request_id: UUID) -> ModelDTO:
        with translate_domain_errors():
            async with self._uow_factory() as uow:
                model = await uow.models.get(model_id, for_update=True)
                if model is None:
                    raise ApplicationError("NOT_FOUND")
                before = model.snapshot()
                if model.rename(name):
                    await uow.models.save(model)
                    await uow.model_logs.add(
                        ModelLog.record(model.id, "update", request_id, before, model.snapshot())
                    )
                    await uow.commit()
                return ModelDTO.from_entity(model)

    async def delete(self, model_id: UUID, request_id: UUID) -> None:
        async with self._uow_factory() as uow:
            model = await uow.models.get(model_id, for_update=True)
            if model is None:
                raise ApplicationError("NOT_FOUND")
            before = model.snapshot()
            await uow.models.delete(model)
            await uow.model_logs.add(ModelLog.record(model.id, "delete", request_id, before, None))
            await uow.commit()

    async def list(self, cursor: str | None, limit: int) -> ModelPage:
        if not 1 <= limit <= 100:
            raise ApplicationError("VALIDATION_ERROR", "query.limit")
        boundary = self._cursor.decode(cursor) if cursor is not None else None
        async with self._uow_factory() as uow:
            rows = await uow.models.list(boundary, limit + 1)
        has_next = len(rows) > limit
        items = [ModelDTO.from_entity(row) for row in rows[:limit]]
        next_cursor = None
        if has_next:
            last = items[-1]
            next_cursor = self._cursor.encode(ModelBoundary(last.created_at, last.id))
        return ModelPage(items, next_cursor, has_next)
