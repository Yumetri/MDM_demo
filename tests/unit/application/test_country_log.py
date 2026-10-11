from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.ports.cursors.country import CountryLogBoundary
from mdm_demo.application.ports.repositories.country_log_repository import CountryLogRepository
from mdm_demo.application.use_cases.country_log import CountryLogUseCases
from mdm_demo.domain.entities.country_log import CountryLog
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


@dataclass(slots=True)
class LogOnlyUnitOfWork:
    country_logs: CountryLogRepository
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
    service = CountryLogUseCases(
        lambda: uow, SignedCountryLogCursor("test-key-with-at-least-32-characters")
    )
    assert not hasattr(uow, "countries")
    assert (await service.list(uuid4(), None, 20)).items == []
    with pytest.raises(ApplicationError, match="NOT_FOUND"):
        await service.get(uuid4())
    assert uow.entries == uow.exits == 2


async def test_log_only_uow_reads_records_and_signed_next_page():
    entity_id = uuid4()
    first = CountryLog.record(entity_id, "create", uuid4(), None, {"name": "Example"})
    second = CountryLog.record(entity_id, "delete", uuid4(), {"name": "Example"}, None)
    logs = MagicMock()
    logs.get = AsyncMock(return_value=first)
    logs.list = AsyncMock(side_effect=[[first, second], [second]])
    uow = LogOnlyUnitOfWork(logs)
    codec = SignedCountryLogCursor("test-key-with-at-least-32-characters")
    service = CountryLogUseCases(lambda: uow, codec)
    assert (await service.get(first.id)).id == first.id
    page = await service.list(entity_id, None, 1)
    assert [item.id for item in page.items] == [first.id]
    assert page.has_next and page.next_cursor is not None
    next_page = await service.list(entity_id, page.next_cursor, 1)
    assert [item.id for item in next_page.items] == [second.id]
    assert not next_page.has_next and next_page.next_cursor is None
    logs.list.assert_awaited_with(entity_id, CountryLogBoundary(first.occurred_at, first.id), 2)
    with pytest.raises(ApplicationError, match="INVALID_CURSOR"):
        await service.list(uuid4(), page.next_cursor, 1)
    assert uow.entries == uow.exits == 3
