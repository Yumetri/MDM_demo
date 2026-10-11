from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.model import ModelLogBoundary
from mdm_demo.application.use_cases.model_log import ModelLogUseCases
from mdm_demo.infrastructure.pagination.model_log_cursor import SignedModelLogCursor


def test_log_cursor_roundtrip_scope_and_rotation():
    codec = SignedModelLogCursor("test-key-with-at-least-32-characters")
    model_id = uuid4()
    boundary = ModelLogBoundary(datetime.now(UTC), uuid4())
    token = codec.encode(boundary, model_id)
    assert codec.decode(token, model_id) == boundary
    for other, target in [
        (codec, uuid4()),
        (SignedModelLogCursor("another-key-with-at-least-32-characters"), model_id),
    ]:
        with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
            other.decode(token, target)


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_log_limit_does_not_open_uow(limit):
    factory = MagicMock()
    model_service = ModelLogUseCases(factory, MagicMock())
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await model_service.list(uuid4(), None, limit)
    factory.assert_not_called()


async def test_log_reads_do_not_check_model_or_commit():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.model_logs.list = AsyncMock(return_value=[])
    uow.model_logs.get = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    model_service = ModelLogUseCases(lambda: uow, MagicMock())
    assert (await model_service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await model_service.get(uuid4())
    uow.models.get.assert_not_called()
    uow.commit.assert_not_awaited()
