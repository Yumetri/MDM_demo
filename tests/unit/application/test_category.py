from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.category import DuplicateCategoryCode, DuplicateCategoryName
from mdm_demo.application.use_cases.category import CategoryUseCases
from mdm_demo.domain.entities.category import Category


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.categories.add = AsyncMock()
    uow.categories.save = AsyncMock()
    uow.categories.get = AsyncMock(return_value=Category.create("Smartphone", "SMA"))
    uow.category_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("error_type", "code", "field"),
    [
        (DuplicateCategoryName, "CATEGORY_NAME_DUPLICATE", "body.name"),
        (DuplicateCategoryCode, "CATEGORY_CODE_DUPLICATE", "body.code"),
    ],
)
async def test_create_unique_failure_rolls_back_without_log(
    category_cursor_codec, error_type, code, field
):
    uow = fake_uow()
    uow.categories.add.side_effect = error_type
    service = CategoryUseCases(lambda: uow, category_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create("Smartphone", "SMA", uuid4())
    assert (error.value.code, error.value.field) == (code, field)
    uow.commit.assert_not_awaited()
    uow.category_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_duplicate_name_on_update_is_translated(category_cursor_codec):
    uow = fake_uow()
    uow.categories.save.side_effect = DuplicateCategoryName
    service = CategoryUseCases(lambda: uow, category_cursor_codec)
    with pytest.raises(ApplicationError, match="CATEGORY_NAME_DUPLICATE"):
        await service.rename(uuid4(), "Tablet", uuid4())
    uow.category_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_noop_has_no_save_log_commit(category_cursor_codec):
    uow = fake_uow()
    category = uow.categories.get.return_value
    result = await CategoryUseCases(lambda: uow, category_cursor_codec).rename(
        category.id, " smartphone ", uuid4()
    )
    assert result.updated_at == category.updated_at
    uow.categories.get.assert_awaited_once_with(category.id, for_update=True)
    uow.categories.save.assert_not_awaited()
    uow.category_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_invalid_code_before_transaction(category_cursor_codec):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await CategoryUseCases(factory, category_cursor_codec).create("Smartphone", "K!1", uuid4())
    factory.assert_not_called()


async def test_auto_duplicate_has_distinct_error(category_cursor_codec):
    uow = fake_uow()
    uow.categories.add.side_effect = DuplicateCategoryCode
    with pytest.raises(ApplicationError, match="DIMENSION_AUTO_CODE_DUPLICATE"):
        await CategoryUseCases(lambda: uow, category_cursor_codec).create(
            "Smartwatch", None, uuid4()
        )
    uow.commit.assert_not_awaited()
    uow.category_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_unavailable_auto_does_not_open_transaction(category_cursor_codec):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="DIMENSION_AUTO_CODE_UNAVAILABLE") as error:
        await CategoryUseCases(factory, category_cursor_codec).create("스마트폰", None, uuid4())
    assert error.value.field == "body.code" and error.value.dimension == "category"
    factory.assert_not_called()
