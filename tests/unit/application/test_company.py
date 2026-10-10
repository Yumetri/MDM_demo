from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError, DuplicateCompanyCode
from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.domain.entities.company import Company


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.companies = MagicMock()
    uow.companies.add = AsyncMock()
    uow.companies.get = AsyncMock()
    uow.company_logs = MagicMock()
    uow.company_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("code", "expected"),
    [(None, "DIMENSION_AUTO_CODE_DUPLICATE"), ("SAM", "COMPANY_CODE_DUPLICATE")],
)
async def test_duplicate_is_mapped_by_code_origin(cursor_codec, code, expected):
    uow = fake_uow()
    uow.companies.add.side_effect = DuplicateCompanyCode
    service = CompanyUseCases(lambda: uow, cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create("Samsung", code, uuid4())
    assert error.value.code == expected
    uow.commit.assert_not_awaited()
    uow.company_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_domain_error_translated_before_transaction(cursor_codec):
    factory = MagicMock()
    service = CompanyUseCases(factory, cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create("LG", None, uuid4())
    assert error.value.code == "DIMENSION_AUTO_CODE_UNAVAILABLE"
    factory.assert_not_called()


async def test_noop_has_no_log_or_commit(cursor_codec):
    uow = fake_uow()
    company = Company.create("Samsung")
    uow.companies.get.return_value = company
    service = CompanyUseCases(lambda: uow, cursor_codec)
    result = await service.rename(company.id, " Samsung ", uuid4())
    assert result.updated_at == company.updated_at
    uow.companies.get.assert_awaited_once_with(company.id, for_update=True)
    uow.company_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
