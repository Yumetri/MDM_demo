from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursor import CountryLogBoundary
from mdm_demo.application.use_cases.country_log import CountryLogUseCases
from mdm_demo.infrastructure.pagination.country_log_cursor import SignedCountryLogCursor


def test_log_cursor_roundtrip_scope_and_rotation():
    codec = SignedCountryLogCursor("test-key-with-at-least-32-characters")
    country_id = uuid4()
    boundary = CountryLogBoundary(datetime.now(UTC), uuid4())
    token = codec.encode(boundary, country_id)
    assert codec.decode(token, country_id) == boundary
    for other, target in [
        (codec, uuid4()),
        (SignedCountryLogCursor("another-key-with-at-least-32-characters"), country_id),
    ]:
        with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
            other.decode(token, target)


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_log_limit_does_not_open_uow(limit):
    factory = MagicMock()
    country_service = CountryLogUseCases(factory, MagicMock())
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await country_service.list(uuid4(), None, limit)
    factory.assert_not_called()


async def test_log_reads_do_not_check_country_or_commit():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.country_logs.list = AsyncMock(return_value=[])
    uow.country_logs.get = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    country_service = CountryLogUseCases(lambda: uow, MagicMock())
    assert (await country_service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await country_service.get(uuid4())
    uow.countries.get.assert_not_called()
    uow.commit.assert_not_awaited()
