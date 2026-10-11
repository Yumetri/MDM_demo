from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.brand import BrandLogBoundary
from mdm_demo.application.ports.repositories.brand_log_repository import BrandLogRepository
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.domain.entities.brand_log import BrandLog
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


@dataclass(slots=True)
class LogOnlyUnitOfWork:
    brand_logs: BrandLogRepository
    entries: int = 0
    exits: int = 0

    async def __aenter__(self) -> Self:
        self.entries += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.exits += 1

    async def commit(self) -> None:
        raise AssertionError("Log reads must not commit")


async def test_log_reads_accept_typed_uow_without_entity_repository():
    logs = MagicMock()
    logs.list = AsyncMock(return_value=[])
    logs.get = AsyncMock(return_value=None)
    uow = LogOnlyUnitOfWork(logs)
    service = BrandLogUseCases(
        lambda: uow, SignedBrandLogCursor("test-key-with-at-least-32-characters")
    )
    assert not hasattr(uow, "brands")
    assert (await service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await service.get(uuid4())
    assert uow.entries == uow.exits == 2


async def test_log_only_uow_reads_records_and_signed_next_page():
    entity_id = uuid4()
    first = BrandLog.record(entity_id, "create", uuid4(), None, {"name": "Example"})
    second = BrandLog.record(entity_id, "delete", uuid4(), {"name": "Example"}, None)
    logs = MagicMock()
    logs.get = AsyncMock(return_value=first)
    logs.list = AsyncMock(side_effect=[[first, second], [second]])
    uow = LogOnlyUnitOfWork(logs)
    codec = SignedBrandLogCursor("test-key-with-at-least-32-characters")
    service = BrandLogUseCases(lambda: uow, codec)
    assert (await service.get(first.id)).id == first.id
    page = await service.list(entity_id, None, 1)
    assert [item.id for item in page.items] == [first.id]
    assert page.has_next and page.next_cursor is not None
    next_page = await service.list(entity_id, page.next_cursor, 1)
    assert [item.id for item in next_page.items] == [second.id]
    assert not next_page.has_next and next_page.next_cursor is None
    logs.list.assert_awaited_with(entity_id, BrandLogBoundary(first.occurred_at, first.id), 2)
    with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
        await service.list(uuid4(), page.next_cursor, 1)
    assert uow.entries == uow.exits == 3
