from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.errors.network import DuplicateNetworkCode, DuplicateNetworkName
from mdm_demo.application.use_cases.network import NetworkUseCases
from mdm_demo.domain.entities.network import Network


def fake_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.networks.add = AsyncMock()
    uow.networks.save = AsyncMock()
    uow.networks.get = AsyncMock(return_value=Network.create("Korea", "KOR"))
    uow.network_logs.add = AsyncMock()
    return uow


@pytest.mark.parametrize(
    ("error_type", "code", "field"),
    [
        (DuplicateNetworkName, "NETWORK_NAME_DUPLICATE", "body.name"),
        (DuplicateNetworkCode, "NETWORK_CODE_DUPLICATE", "body.code"),
    ],
)
async def test_create_unique_failure_rolls_back_without_log(
    network_cursor_codec, error_type, code, field
):
    uow = fake_uow()
    uow.networks.add.side_effect = error_type
    service = NetworkUseCases(lambda: uow, network_cursor_codec)
    with pytest.raises(ApplicationError) as error:
        await service.create("Korea", "KOR", uuid4())
    assert (error.value.code, error.value.field) == (code, field)
    uow.commit.assert_not_awaited()
    uow.network_logs.add.assert_not_awaited()
    uow.__aexit__.assert_awaited_once()


async def test_duplicate_name_on_update_is_translated(network_cursor_codec):
    uow = fake_uow()
    uow.networks.save.side_effect = DuplicateNetworkName
    service = NetworkUseCases(lambda: uow, network_cursor_codec)
    with pytest.raises(ApplicationError, match="NETWORK_NAME_DUPLICATE"):
        await service.rename(uuid4(), "Japan", uuid4())
    uow.network_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_noop_has_no_save_log_commit(network_cursor_codec):
    uow = fake_uow()
    network = uow.networks.get.return_value
    result = await NetworkUseCases(lambda: uow, network_cursor_codec).rename(
        network.id, " korea ", uuid4()
    )
    assert result.updated_at == network.updated_at
    uow.networks.get.assert_awaited_once_with(network.id, for_update=True)
    uow.networks.save.assert_not_awaited()
    uow.network_logs.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_invalid_code_before_transaction(network_cursor_codec):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
        await NetworkUseCases(factory, network_cursor_codec).create("Korea", "K-01", uuid4())
    factory.assert_not_called()


async def test_auto_code_duplicate_is_distinct(network_cursor_codec):
    uow = fake_uow()
    uow.networks.add.side_effect = DuplicateNetworkCode
    with pytest.raises(ApplicationError, match="DIMENSION_AUTO_CODE_DUPLICATE"):
        await NetworkUseCases(lambda: uow, network_cursor_codec).create("LTE", None, uuid4())
    uow.commit.assert_not_awaited()
    uow.network_logs.add.assert_not_awaited()


@pytest.mark.parametrize("name", ["이동통신", "A" * 21])
async def test_auto_unavailable_does_not_open_transaction(network_cursor_codec, name):
    factory = MagicMock()
    with pytest.raises(ApplicationError, match="DIMENSION_AUTO_CODE_UNAVAILABLE"):
        await NetworkUseCases(factory, network_cursor_codec).create(name, None, uuid4())
    factory.assert_not_called()
