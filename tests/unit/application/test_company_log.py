from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursor import CompanyLogBoundary
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.infrastructure.pagination.company_log_cursor import SignedCompanyLogCursor


def test_log_cursor_roundtrip_scope_and_rotation():
    codec = SignedCompanyLogCursor("test-key-with-at-least-32-characters")
    company_id = uuid4()
    boundary = CompanyLogBoundary(datetime.now(UTC), uuid4())
    token = codec.encode(boundary, company_id)
    assert codec.decode(token, company_id) == boundary
    for other, target in [
        (codec, uuid4()),
        (SignedCompanyLogCursor("another-key-with-at-least-32-characters"), company_id),
    ]:
        with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
            other.decode(token, target)


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_log_limit_does_not_open_uow(limit):
    factory = MagicMock()
    service = CompanyLogUseCases(factory, MagicMock())
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await service.list(uuid4(), None, limit)
    factory.assert_not_called()


async def test_log_reads_do_not_check_company_or_commit():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.company_logs.list = AsyncMock(return_value=[])
    uow.company_logs.get = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    service = CompanyLogUseCases(lambda: uow, MagicMock())
    assert (await service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await service.get(uuid4())
    uow.companies.get.assert_not_called()
    uow.commit.assert_not_awaited()
