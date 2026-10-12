from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.year import DuplicateYear
from mdm_demo.application.use_cases.year import YearUseCases
from mdm_demo.domain.entities.year import Year


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.years = MagicMock()
    uow.years.add = AsyncMock()
    uow.years.save = AsyncMock()
    uow.years.get = AsyncMock(return_value=Year.create(2024))
    uow.year_logs = MagicMock()
    uow.year_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize("operation", ["create", "change_year"])
async def test_duplicate_mapping_rolls_back_without_commit(year_cursor_codec, operation):
    uow = fake_uow()
    service = YearUseCases(lambda: uow, year_cursor_codec)
    uow.years.add.side_effect = DuplicateYear
    uow.years.save.side_effect = DuplicateYear
    with pytest.raises(ApplicationError) as error:
        if operation == "create":
            await service.create(2025, uuid4())
        else:
            await service.change_year(uuid4(), 2025, uuid4())
    assert error.value.code == "YEAR_DUPLICATE"
    uow.commit.assert_not_awaited()
    uow.year_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_noop_does_not_write(year_cursor_codec):
    uow = fake_uow()
    entity = uow.years.get.return_value
    service = YearUseCases(lambda: uow, year_cursor_codec)
    result = await service.change_year(entity.id, 2024, uuid4())
    assert result.updated_at == entity.updated_at
    uow.years.get.assert_awaited_once_with(entity.id, for_update=True)
    uow.years.save.assert_not_awaited()
    uow.commit.assert_not_awaited()
    uow.year_logs.add.assert_not_awaited()


async def test_validation_before_create_transaction(year_cursor_codec):
    factory = MagicMock()
    service = YearUseCases(factory, year_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create(1899, uuid4())
    assert error.value.code == "VALIDATION_ERROR"
    factory.assert_not_called()
