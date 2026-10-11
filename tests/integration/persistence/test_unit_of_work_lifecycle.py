import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mdm_demo.infrastructure.persistence.units_of_work.brand import SqlAlchemyBrandUnitOfWork
from mdm_demo.infrastructure.persistence.units_of_work.company import SqlAlchemyCompanyUnitOfWork
from mdm_demo.infrastructure.persistence.units_of_work.country import SqlAlchemyCountryUnitOfWork
from mdm_demo.infrastructure.persistence.units_of_work.model import SqlAlchemyModelUnitOfWork

UOW_TYPES = (
    SqlAlchemyCompanyUnitOfWork,
    SqlAlchemyModelUnitOfWork,
    SqlAlchemyBrandUnitOfWork,
    SqlAlchemyCountryUnitOfWork,
)


@pytest.mark.parametrize("uow_type", UOW_TYPES)
@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_repository_binding_failure_releases_session_and_allows_reentry(
    monkeypatch, uow_type, failure
):
    failed_session = AsyncMock(spec=AsyncSession)
    next_session = AsyncMock(spec=AsyncSession)
    factory = Mock(side_effect=[failed_session, next_session])
    uow = uow_type(factory)
    with monkeypatch.context() as patch:
        patch.setattr(uow, "_bind_repositories", Mock(side_effect=failure))
        with pytest.raises(failure):
            async with uow:
                pytest.fail("Failed initialization must not enter transaction body")
    failed_session.rollback.assert_awaited_once()
    failed_session.close.assert_awaited_once()
    failed_session.commit.assert_not_awaited()

    async with uow:
        await uow.commit()
    assert factory.call_count == 2
    next_session.commit.assert_awaited_once()
    next_session.close.assert_awaited_once()


@pytest.mark.parametrize("uow_type", UOW_TYPES)
async def test_nested_entry_does_not_replace_active_transaction(uow_type):
    session = AsyncMock(spec=AsyncSession)
    factory = Mock(return_value=session)
    uow = uow_type(factory)
    async with uow:
        with pytest.raises(RuntimeError, match="already active"):
            await uow.__aenter__()
        session.close.assert_not_awaited()
        await uow.commit()
    factory.assert_called_once()
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()
