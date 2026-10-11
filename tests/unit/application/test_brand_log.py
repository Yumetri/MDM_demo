from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursor import BrandLogBoundary
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.infrastructure.pagination.brand_log_cursor import SignedBrandLogCursor


def test_log_cursor_roundtrip_scope_and_rotation():
    codec = SignedBrandLogCursor("test-key-with-at-least-32-characters")
    brand_id = uuid4()
    boundary = BrandLogBoundary(datetime.now(UTC), uuid4())
    token = codec.encode(boundary, brand_id)
    assert codec.decode(token, brand_id) == boundary
    for other, target in [
        (codec, uuid4()),
        (SignedBrandLogCursor("another-key-with-at-least-32-characters"), brand_id),
    ]:
        with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
            other.decode(token, target)


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_log_limit_does_not_open_uow(limit):
    factory = MagicMock()
    brand_service = BrandLogUseCases(factory, MagicMock())
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await brand_service.list(uuid4(), None, limit)
    factory.assert_not_called()


async def test_log_reads_do_not_check_brand_or_commit():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.brand_logs.list = AsyncMock(return_value=[])
    uow.brand_logs.get = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    brand_service = BrandLogUseCases(lambda: uow, MagicMock())
    assert (await brand_service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await brand_service.get(uuid4())
    uow.brands.get.assert_not_called()
    uow.commit.assert_not_awaited()
