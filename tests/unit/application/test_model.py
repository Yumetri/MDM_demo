from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.model import DuplicateModelCode
from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.domain.entities.model import Model


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.models = MagicMock()
    uow.models.add = AsyncMock()
    uow.models.get = AsyncMock()
    uow.model_logs = MagicMock()
    uow.model_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("code", "expected"),
    [(None, "DIMENSION_AUTO_CODE_DUPLICATE"), ("SAM", "MODEL_CODE_DUPLICATE")],
)
async def test_duplicate_is_mapped_by_code_origin(model_cursor_codec, code, expected):
    uow = fake_uow()
    uow.models.add.side_effect = DuplicateModelCode
    model_service = ModelUseCases(lambda: uow, model_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await model_service.create("Samsung", code, uuid4())
    assert error.value.code == expected
    uow.commit.assert_not_awaited()
    uow.model_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_domain_error_translated_before_transaction(model_cursor_codec):
    factory = MagicMock()
    model_service = ModelUseCases(factory, model_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await model_service.create("LG", None, uuid4())
    assert error.value.code == "DIMENSION_AUTO_CODE_UNAVAILABLE"
    factory.assert_not_called()


async def test_noop_has_no_log_or_commit(model_cursor_codec):
    uow = fake_uow()
    model = Model.create("Samsung")
    uow.models.get.return_value = model
    model_service = ModelUseCases(lambda: uow, model_cursor_codec)
    result = await model_service.rename(model.id, " Samsung ", uuid4())
    assert result.updated_at == model.updated_at
    uow.models.get.assert_awaited_once_with(model.id, for_update=True)
    uow.model_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
