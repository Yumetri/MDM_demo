from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.country import DuplicateCountryCode, DuplicateCountryName
from mdm_demo.application.use_cases.country import CountryUseCases
from mdm_demo.domain.entities.country import Country


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.countries.add = AsyncMock()
    uow.countries.save = AsyncMock()
    uow.countries.get = AsyncMock(return_value=Country.create("Korea", "KOR"))
    uow.country_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("error_type", "code", "field"),
    [
        (DuplicateCountryName, "COUNTRY_NAME_DUPLICATE", "body.name"),
        (DuplicateCountryCode, "COUNTRY_CODE_DUPLICATE", "body.code"),
    ],
)
async def test_create_unique_failure_rolls_back_without_log(
    country_cursor_codec, error_type, code, field
):
    uow = fake_uow()
    uow.countries.add.side_effect = error_type
    service = CountryUseCases(lambda: uow, country_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create("Korea", "KOR", uuid4())
    assert (error.value.code, error.value.field) == (code, field)
    uow.commit.assert_not_awaited()
    uow.country_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_duplicate_name_on_update_is_translated(country_cursor_codec):
    uow = fake_uow()
    uow.countries.save.side_effect = DuplicateCountryName
    service = CountryUseCases(lambda: uow, country_cursor_codec)
    with pytest.raises(ApplicationError, match="COUNTRY_NAME_DUPLICATE"):
        await service.rename(uuid4(), "Japan", uuid4())
    uow.country_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_noop_has_no_save_log_commit(country_cursor_codec):
    uow = fake_uow()
    country = uow.countries.get.return_value
    result = await CountryUseCases(lambda: uow, country_cursor_codec).rename(
        country.id, " korea ", uuid4()
    )
    assert result.updated_at == country.updated_at
    uow.countries.get.assert_awaited_once_with(country.id, for_update=True)
    uow.countries.save.assert_not_awaited()
    uow.country_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_invalid_code_before_transaction(country_cursor_codec):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await CountryUseCases(factory, country_cursor_codec).create("Korea", "K01", uuid4())
    factory.assert_not_called()
