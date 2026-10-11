from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError, DuplicateBrandCode
from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.domain.entities.brand import Brand


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.brands = MagicMock()
    uow.brands.add = AsyncMock()
    uow.brands.get = AsyncMock()
    uow.brand_logs = MagicMock()
    uow.brand_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("code", "expected"),
    [(None, "DIMENSION_AUTO_CODE_DUPLICATE"), ("SAM", "BRAND_CODE_DUPLICATE")],
)
async def test_duplicate_is_mapped_by_code_origin(brand_cursor_codec, code, expected):
    uow = fake_uow()
    uow.brands.add.side_effect = DuplicateBrandCode
    brand_service = BrandUseCases(lambda: uow, brand_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await brand_service.create("Samsung", code, uuid4())
    assert error.value.code == expected
    uow.commit.assert_not_awaited()
    uow.brand_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_domain_error_translated_before_transaction(brand_cursor_codec):
    factory = MagicMock()
    brand_service = BrandUseCases(factory, brand_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await brand_service.create("LG", None, uuid4())
    assert error.value.code == "DIMENSION_AUTO_CODE_UNAVAILABLE"
    factory.assert_not_called()


async def test_noop_has_no_log_or_commit(brand_cursor_codec):
    uow = fake_uow()
    brand = Brand.create("Samsung")
    uow.brands.get.return_value = brand
    brand_service = BrandUseCases(lambda: uow, brand_cursor_codec)
    result = await brand_service.rename(brand.id, " Samsung ", uuid4())
    assert result.updated_at == brand.updated_at
    uow.brands.get.assert_awaited_once_with(brand.id, for_update=True)
    uow.brand_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
