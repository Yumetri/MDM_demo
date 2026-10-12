import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.use_cases.network import NetworkUseCases
from mdm_demo.domain.entities.network import Network
from mdm_demo.domain.entities.network_log import NetworkLog
from mdm_demo.domain.value_objects.network_code import NetworkCode
from mdm_demo.domain.value_objects.network_name import NetworkName
from mdm_demo.infrastructure.persistence.mappers import network_log_mapper, network_mapper
from mdm_demo.infrastructure.persistence.models.network import NetworkModel
from mdm_demo.infrastructure.persistence.models.network_log import NetworkLogModel
from mdm_demo.infrastructure.persistence.units_of_work.network import SqlAlchemyNetworkUnitOfWork


async def counts(factory):
    async with factory() as session:
        return (
            await session.scalar(select(func.count()).select_from(NetworkModel)),
            await session.scalar(select(func.count()).select_from(NetworkLogModel)),
        )


async def logs(factory, network_id):
    async with factory() as session:
        return list(
            await session.scalars(
                select(NetworkLogModel)
                .where(NetworkLogModel.network_id == network_id)
                .order_by(NetworkLogModel.occurred_at, NetworkLogModel.id)
            )
        )


async def test_mapper_roundtrip_and_commit(database):
    _, factory = database
    network = Network.create(" 삼성  전자 ", "abc")
    log = NetworkLog.record(network.id, "create", uuid4(), None, network.snapshot())
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        await uow.networks.add(network)
        await uow.network_logs.add(log)
        await uow.commit()
    async with factory() as session:
        row = await session.get(NetworkModel, network.id)
        log_row = await session.get(NetworkLogModel, log.id)
        assert row is not None and log_row is not None
        restored = network_mapper.to_domain(row)
        restored_log = network_log_mapper.to_domain(log_row)
        assert restored.snapshot() == network.snapshot()
        assert restored.created_at == network.created_at
        assert restored.updated_at == network.updated_at
        assert restored_log == log
        assert restored_log.before is None and restored_log.after == log.after
        assert restored_log.request_id == log.request_id
        assert restored_log.occurred_at == log.occurred_at


@pytest.mark.parametrize("raise_error", [False, True])
async def test_uncommitted_exit_rolls_back_both(database, raise_error):
    _, factory = database
    try:
        async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
            network = Network.create("KOREA", "KOR")
            await uow.networks.add(network)
            await uow.network_logs.add(
                NetworkLog.record(network.id, "create", uuid4(), None, network.snapshot())
            )
            if raise_error:
                raise RuntimeError("business operation failed")
    except RuntimeError:
        pass
    assert await counts(factory) == (0, 0)


@pytest.mark.parametrize("operation", ["create", "rename", "delete"])
async def test_log_database_failure_rolls_back_network(database, network_service, operation):
    _, factory = database
    initial = (
        await network_service.create("KOREA", "KOR", uuid4()) if operation != "create" else None
    )
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test injected failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE TRIGGER fail_test_log BEFORE INSERT ON network_logs
            FOR EACH ROW EXECUTE FUNCTION fail_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="test injected failure"):
            if initial is None:
                await network_service.create("KOREA", "KOR", uuid4())
            elif operation == "rename":
                await network_service.rename(initial.id, "Changed", uuid4())
            else:
                await network_service.delete(initial.id, uuid4())
        assert await counts(factory) == ((0, 0) if initial is None else (1, 1))
        if initial is not None:
            assert (await network_service.get(initial.id)).name == "KOREA"
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_test_log ON network_logs"))
            await session.execute(text("DROP FUNCTION fail_test_log()"))
            await session.commit()


async def test_commit_failure_cleans_up(database, network_cursor_codec):
    engine, factory = database

    class FailingSession(AsyncSession):
        async def commit(self) -> None:
            raise RuntimeError("injected before commit")

    failing_factory = async_sessionmaker(engine, class_=FailingSession, expire_on_commit=False)
    network_service = NetworkUseCases(
        lambda: SqlAlchemyNetworkUnitOfWork(failing_factory), network_cursor_codec
    )
    with pytest.raises(RuntimeError, match="injected before commit"):
        await network_service.create("KOREA", "KOR", uuid4())
    assert await counts(factory) == (0, 0)
    assert engine.sync_engine.pool.checkedout() == 0


async def test_cancellation_during_commit_cleans_up(database, network_cursor_codec):
    engine, factory = database
    entered = asyncio.Event()

    class WaitingSession(AsyncSession):
        async def commit(self) -> None:
            entered.set()
            await asyncio.Event().wait()

    waiting_factory = async_sessionmaker(engine, class_=WaitingSession, expire_on_commit=False)
    network_service = NetworkUseCases(
        lambda: SqlAlchemyNetworkUnitOfWork(waiting_factory), network_cursor_codec
    )
    task = asyncio.create_task(network_service.create("KOREA", "KOR", uuid4()))
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await counts(factory) == (0, 0)
    assert engine.sync_engine.pool.checkedout() == 0


async def test_repeated_cancellation_waits_for_cleanup(database):
    engine, factory = database
    cleanup_started = asyncio.Event()
    allow_cleanup = asyncio.Event()

    class SlowRollbackSession(AsyncSession):
        async def rollback(self) -> None:
            cleanup_started.set()
            await allow_cleanup.wait()
            await super().rollback()

    slow_factory = async_sessionmaker(engine, class_=SlowRollbackSession, expire_on_commit=False)

    async def change():
        async with SqlAlchemyNetworkUnitOfWork(slow_factory) as uow:
            await uow.networks.add(Network.create("KOREA", "KOR"))

    task = asyncio.create_task(change())
    await asyncio.wait_for(cleanup_started.wait(), 5)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    allow_cleanup.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await counts(factory) == (0, 0)
    assert engine.sync_engine.pool.checkedout() == 0


async def test_concurrent_create_unique_code_and_single_log(database, network_service):
    _, factory = database
    results = await asyncio.gather(
        network_service.create("KOREA", "KOR", uuid4()),
        network_service.create("OTHER", "kor", uuid4()),
        return_exceptions=True,
    )
    failures = [result for result in results if isinstance(result, ApplicationError)]
    assert len(failures) == 1
    assert failures[0].code in {"NETWORK_CODE_DUPLICATE"}
    assert await counts(factory) == (1, 1)


async def test_concurrent_renames_preserve_history_chain(database, network_service):
    _, factory = database
    network = await network_service.create("KOREA", "KOR", uuid4())
    await asyncio.gather(
        network_service.rename(network.id, "Name A", uuid4()),
        network_service.rename(network.id, "Name B", uuid4()),
    )
    history = await logs(factory, network.id)
    assert [item.operation for item in history] == ["create", "update", "update"]
    assert history[1].before == history[0].after
    assert history[2].before == history[1].after
    assert history[2].after["name"] == (await network_service.get(network.id)).name


async def wait_for_lock_waiter(factory):
    async with asyncio.timeout(5):
        while True:
            async with factory() as session:
                waiting = await session.scalar(
                    text("""SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database() AND wait_event_type = 'Lock'""")
                )
            if waiting:
                return
            await asyncio.sleep(0.01)


async def test_update_delete_race_logs_locked_current_value(database, network_service):
    _, factory = database
    network = await network_service.create("KOREA", "KOR", uuid4())
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        entity = await uow.networks.get(network.id, for_update=True)
        assert entity is not None
        before = entity.snapshot()
        entity.rename("Updated before delete")
        await uow.networks.save(entity)
        await uow.network_logs.add(
            NetworkLog.record(entity.id, "update", uuid4(), before, entity.snapshot())
        )
        delete_task = asyncio.create_task(network_service.delete(network.id, uuid4()))
        try:
            await wait_for_lock_waiter(factory)
            await uow.commit()
        except BaseException:
            delete_task.cancel()
            await asyncio.gather(delete_task, return_exceptions=True)
            raise
    await asyncio.wait_for(delete_task, 5)
    history = await logs(factory, network.id)
    assert history[-1].operation == "delete"
    assert history[-1].before == history[-2].after
    assert history[-1].after is None
    assert await counts(factory) == (0, 3)


async def test_delete_then_update_waiter_returns_not_found(database, network_service):
    _, factory = database
    network = await network_service.create("KOREA", "KOR", uuid4())
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        entity = await uow.networks.get(network.id, for_update=True)
        assert entity is not None
        await uow.networks.delete(entity)
        await uow.network_logs.add(
            NetworkLog.record(entity.id, "delete", uuid4(), entity.snapshot(), None)
        )
        rename_task = asyncio.create_task(network_service.rename(network.id, "Too late", uuid4()))
        try:
            await wait_for_lock_waiter(factory)
            await uow.commit()
        except BaseException:
            rename_task.cancel()
            await asyncio.gather(rename_task, return_exceptions=True)
            raise
    with pytest.raises(ApplicationError) as error:
        await asyncio.wait_for(rename_task, 5)
    assert error.value.code == "NOT_FOUND"
    assert await counts(factory) == (0, 2)


async def test_append_only_log_and_unrelated_constraint_not_duplicate(database, network_service):
    _, factory = database
    network = await network_service.create("KOREA", "KOR", uuid4())
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("DELETE FROM network_logs"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text("UPDATE network_logs SET operation = operation"))
        await session.rollback()
    # A duplicate primary key must not be misreported as duplicate network code.
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        existing = await uow.networks.get(network.id)
        assert existing is not None
        with pytest.raises(IntegrityError):
            await uow.networks.add(existing)


async def test_cursor_same_timestamp_and_deleted_boundary(database, network_service):
    _, factory = database
    now = datetime.now(UTC)
    entities = [
        Network(UUID(int=i), NetworkName(code), NetworkCode(code), now, now)
        for i, code in enumerate(["AAA", "AAB", "AAC"], 1)
    ]
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        for entity in entities:
            await uow.networks.add(entity)
        await uow.commit()
    first = await network_service.list(None, 1)
    assert first.items[0].id == UUID(int=3) and first.has_next
    await network_service.delete(first.items[0].id, uuid4())
    second = await network_service.list(first.next_cursor, 1)
    third = await network_service.list(second.next_cursor, 1)
    assert second.items[0].id == UUID(int=2)
    assert third.items[0].id == UUID(int=1)
    assert third.next_cursor is None and not third.has_next


async def test_database_rejects_commit_and_rolls_back_both(database, network_service):
    engine, factory = database
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_deferred_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'deferred commit failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE CONSTRAINT TRIGGER fail_deferred_test_log
            AFTER INSERT ON network_logs DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION fail_deferred_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="deferred commit failure"):
            await network_service.create("KOREA", "KOR", uuid4())
        assert await counts(factory) == (0, 0)
        assert engine.sync_engine.pool.checkedout() == 0
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_deferred_test_log ON network_logs"))
            await session.execute(text("DROP FUNCTION fail_deferred_test_log()"))
            await session.commit()


async def test_concurrent_create_same_normalized_name(database, network_service):
    _, factory = database
    results = await asyncio.gather(
        network_service.create(" korea ", "KOR", uuid4()),
        network_service.create("Korea", "NEW", uuid4()),
        return_exceptions=True,
    )
    failures = [r for r in results if isinstance(r, ApplicationError)]
    assert len(failures) == 1 and failures[0].code == "NETWORK_NAME_DUPLICATE"
    assert await counts(factory) == (1, 1)


async def test_concurrent_distinct_rows_rename_to_same_name(database, network_service):
    _, factory = database
    one = await network_service.create("Korea", "KOR", uuid4())
    two = await network_service.create("Japan", "JPN", uuid4())
    results = await asyncio.gather(
        network_service.rename(one.id, " shared ", uuid4()),
        network_service.rename(two.id, "Shared", uuid4()),
        return_exceptions=True,
    )
    failures = [r for r in results if isinstance(r, ApplicationError)]
    assert len(failures) == 1 and failures[0].code == "NETWORK_NAME_DUPLICATE"
    assert await counts(factory) == (2, 3)
    for original in [one, two]:
        current = await network_service.get(original.id)
        history = await logs(factory, original.id)
        if current.name == "SHARED":
            assert len(history) == 2 and history[1].before == history[0].after
        else:
            assert current == original and len(history) == 1


async def test_update_unrelated_database_error_is_not_duplicate(database, network_service):
    _, factory = database
    network = await network_service.create("Korea", "KOR", uuid4())
    async with factory() as session:
        await session.execute(
            text(
                "ALTER TABLE networks ADD CONSTRAINT test_forbidden_name "
                "CHECK (name != 'FORBIDDEN')"
            )
        )
        await session.commit()
    try:
        with pytest.raises(IntegrityError):
            await network_service.rename(network.id, "Forbidden", uuid4())
        assert await counts(factory) == (1, 1)
        assert (await network_service.get(network.id)).name == "KOREA"
    finally:
        async with factory() as session:
            await session.execute(text("ALTER TABLE networks DROP CONSTRAINT test_forbidden_name"))
            await session.commit()


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("VALID", ""),
        ("VALID", "a"),
        ("VALID", "LTE-A"),
        ("VALID", "A" * 21),
        ("", "OK"),
        (" PADDED ", "OK"),
        ("A" * 101, "OK"),
    ],
)
async def test_database_enforces_name_and_code_shape(database, name, code):
    _, factory = database
    async with factory() as session:
        with pytest.raises(DBAPIError) as error:
            await session.execute(
                text(
                    "INSERT INTO networks (id,name,code,created_at,updated_at) "
                    "VALUES (:id,:name,:code,now(),now())"
                ),
                {"id": uuid4(), "name": name, "code": code},
            )
        expected_state = "22001" if len(name) > 100 or len(code) > 20 else "23514"
        original = error.value.orig
        assert original is not None
        assert getattr(original.__cause__, "sqlstate", None) == expected_state
        await session.rollback()
    assert await counts(factory) == (0, 0)
