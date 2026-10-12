from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.memory import DuplicateMemoryCapacity
from mdm_demo.application.use_cases.memory import MemoryUseCases
from mdm_demo.domain.entities.memory import Memory


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.memories.add = AsyncMock()
    uow.memories.save = AsyncMock()
    uow.memories.get = AsyncMock()
    uow.memory_logs.add = AsyncMock()
    return uow


async def test_invalid_domain_value_does_not_start_transaction(memory_cursor_codec):
    factory = MagicMock()
    service = MemoryUseCases(factory, memory_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create(True, "GB", uuid4())
    assert error.value.code == "VALIDATION_ERROR" and error.value.field == "body.capacity"
    factory.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "change"])
async def test_duplicates_have_same_error_and_no_log_or_commit(memory_cursor_codec, operation):
    uow = fake_uow()
    memory = Memory.create(256, "GB")
    uow.memories.get.return_value = memory
    uow.memories.add.side_effect = DuplicateMemoryCapacity
    uow.memories.save.side_effect = DuplicateMemoryCapacity
    service = MemoryUseCases(lambda: uow, memory_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        if operation == "create":
            await service.create(1, "TB", uuid4())
        else:
            await service.change_size(memory.id, 1000, "GB", uuid4())
    assert error.value.code == "MEMORY_CAPACITY_DUPLICATE"
    assert error.value.field == "body.capacity"
    uow.commit.assert_not_awaited()
    uow.memory_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_noop_and_equivalent_representation_have_different_transaction_effects(
    memory_cursor_codec,
):
    uow = fake_uow()
    memory = Memory.create(1, "TB")
    uow.memories.get.return_value = memory
    service = MemoryUseCases(lambda: uow, memory_cursor_codec)
    before = memory.snapshot()
    updated = memory.updated_at
    assert (await service.change_size(memory.id, 1, " tb ", uuid4())).updated_at == updated
    uow.memories.save.assert_not_awaited()
    uow.memory_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    request_id = uuid4()
    result = await service.change_size(memory.id, 1000, "GB", request_id)
    assert result.code == "1000GB" and result.id == memory.id
    log = uow.memory_logs.add.call_args.args[0]
    assert log.before == before and log.after["capacity"] == 1000
    assert log.request_id == request_id and log.operation == "update"
    uow.commit.assert_awaited_once()
    uow.memories.get.assert_awaited_with(memory.id, for_update=True)


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_limit_does_not_open_uow(limit):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await MemoryUseCases(factory, MagicMock()).list(None, limit)
    factory.assert_not_called()
