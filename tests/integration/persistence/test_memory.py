import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.use_cases.memory import MemoryUseCases
from mdm_demo.domain.entities.memory import Memory
from mdm_demo.domain.entities.memory_log import MemoryLog
from mdm_demo.infrastructure.persistence.mappers import memory_log_mapper, memory_mapper
from mdm_demo.infrastructure.persistence.models.memory import MemoryModel
from mdm_demo.infrastructure.persistence.models.memory_log import MemoryLogModel
from mdm_demo.infrastructure.persistence.units_of_work.memory import SqlAlchemyMemoryUnitOfWork


async def counts(factory):
    async with factory() as session:
        return (
            await session.scalar(select(func.count()).select_from(MemoryModel)),
            await session.scalar(select(func.count()).select_from(MemoryLogModel)),
        )


async def logs(factory, memory_id):
    async with factory() as session:
        return list(
            await session.scalars(
                select(MemoryLogModel)
                .where(MemoryLogModel.memory_id == memory_id)
                .order_by(MemoryLogModel.occurred_at, MemoryLogModel.id)
            )
        )


async def test_mapper_roundtrip_generated_capacity_and_integer_log(database):
    _, factory = database
    memory = Memory.create(2147483647, "tb")
    log = MemoryLog.record(memory.id, "create", uuid4(), None, memory.snapshot())
    async with SqlAlchemyMemoryUnitOfWork(factory) as uow:
        await uow.memories.add(memory)
        await uow.memory_logs.add(log)
        await uow.commit()
    async with factory() as session:
        row = await session.get(MemoryModel, memory.id)
        log_row = await session.get(MemoryLogModel, log.id)
        assert row is not None and log_row is not None
        assert row.capacity_gb == 2147483647000 and row.code == "2147483647TB"
        restored = memory_mapper.to_domain(row)
        restored_log = memory_log_mapper.to_domain(log_row)
        assert restored.snapshot() == memory.snapshot()
        assert restored.created_at == memory.created_at and restored.updated_at == memory.updated_at
        assert restored_log.before is None and restored_log.after == log.after
        assert (
            restored_log.request_id == log.request_id
            and restored_log.occurred_at == log.occurred_at
        )
        assert restored_log.after is not None and type(restored_log.after["capacity"]) is int


@pytest.mark.parametrize("raise_error", [False, True])
async def test_uncommitted_exit_rolls_back_both(database, raise_error):
    _, factory = database
    try:
        async with SqlAlchemyMemoryUnitOfWork(factory) as uow:
            memory = Memory.create(256, "GB")
            await uow.memories.add(memory)
            await uow.memory_logs.add(
                MemoryLog.record(memory.id, "create", uuid4(), None, memory.snapshot())
            )
            if raise_error:
                raise RuntimeError("business operation failed")
    except RuntimeError:
        pass
    assert await counts(factory) == (0, 0)


@pytest.mark.parametrize("operation", ["create", "rename", "delete"])
async def test_log_database_failure_rolls_back_memory(database, memory_service, operation):
    _, factory = database
    initial = await memory_service.create(256, "GB", uuid4()) if operation != "create" else None
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test injected failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE TRIGGER fail_test_log BEFORE INSERT ON memory_logs
            FOR EACH ROW EXECUTE FUNCTION fail_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="test injected failure"):
            if initial is None:
                await memory_service.create(256, "GB", uuid4())
            elif operation == "rename":
                await memory_service.change_size(initial.id, 512, "GB", uuid4())
            else:
                await memory_service.delete(initial.id, uuid4())
        assert await counts(factory) == ((0, 0) if initial is None else (1, 1))
        if initial is not None:
            assert (await memory_service.get(initial.id)).capacity == 256
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_test_log ON memory_logs"))
            await session.execute(text("DROP FUNCTION fail_test_log()"))
            await session.commit()


async def test_commit_failure_cleans_up(database, memory_cursor_codec):
    engine, factory = database

    class FailingSession(AsyncSession):
        async def commit(self) -> None:
            raise RuntimeError("injected before commit")

    failing_factory = async_sessionmaker(engine, class_=FailingSession, expire_on_commit=False)
    memory_service = MemoryUseCases(
        lambda: SqlAlchemyMemoryUnitOfWork(failing_factory), memory_cursor_codec
    )
    with pytest.raises(RuntimeError, match="injected before commit"):
        await memory_service.create(256, "GB", uuid4())
    assert await counts(factory) == (0, 0)
    assert engine.sync_engine.pool.checkedout() == 0


async def test_cancellation_during_commit_cleans_up(database, memory_cursor_codec):
    engine, factory = database
    entered = asyncio.Event()

    class WaitingSession(AsyncSession):
        async def commit(self) -> None:
            entered.set()
            await asyncio.Event().wait()

    waiting_factory = async_sessionmaker(engine, class_=WaitingSession, expire_on_commit=False)
    memory_service = MemoryUseCases(
        lambda: SqlAlchemyMemoryUnitOfWork(waiting_factory), memory_cursor_codec
    )
    task = asyncio.create_task(memory_service.create(256, "GB", uuid4()))
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
        async with SqlAlchemyMemoryUnitOfWork(slow_factory) as uow:
            await uow.memories.add(Memory.create(256, "GB"))

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


async def test_update_delete_race_logs_locked_current_value(database, memory_service):
    _, factory = database
    memory = await memory_service.create(256, "GB", uuid4())
    async with SqlAlchemyMemoryUnitOfWork(factory) as uow:
        entity = await uow.memories.get(memory.id, for_update=True)
        assert entity is not None
        before = entity.snapshot()
        entity.change_size(512, "GB")
        await uow.memories.save(entity)
        await uow.memory_logs.add(
            MemoryLog.record(entity.id, "update", uuid4(), before, entity.snapshot())
        )
        delete_task = asyncio.create_task(memory_service.delete(memory.id, uuid4()))
        try:
            await wait_for_lock_waiter(factory)
            await uow.commit()
        except BaseException:
            delete_task.cancel()
            await asyncio.gather(delete_task, return_exceptions=True)
            raise
    await asyncio.wait_for(delete_task, 5)
    history = await logs(factory, memory.id)
    assert history[-1].operation == "delete"
    assert history[-1].before == history[-2].after
    assert history[-1].after is None
    assert await counts(factory) == (0, 3)


async def test_delete_then_update_waiter_returns_not_found(database, memory_service):
    _, factory = database
    memory = await memory_service.create(256, "GB", uuid4())
    async with SqlAlchemyMemoryUnitOfWork(factory) as uow:
        entity = await uow.memories.get(memory.id, for_update=True)
        assert entity is not None
        await uow.memories.delete(entity)
        await uow.memory_logs.add(
            MemoryLog.record(entity.id, "delete", uuid4(), entity.snapshot(), None)
        )
        rename_task = asyncio.create_task(memory_service.change_size(memory.id, 512, "GB", uuid4()))
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


async def test_append_only_log_and_unrelated_constraint_not_duplicate(database, memory_service):
    _, factory = database
    memory = await memory_service.create(256, "GB", uuid4())
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("DELETE FROM memory_logs"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text("UPDATE memory_logs SET operation = operation"))
        await session.rollback()
    # A duplicate primary key must not be misreported as duplicate memory code.
    async with SqlAlchemyMemoryUnitOfWork(factory) as uow:
        existing = await uow.memories.get(memory.id)
        assert existing is not None
        with pytest.raises(IntegrityError):
            await uow.memories.add(existing)


async def test_database_rejects_commit_and_rolls_back_both(database, memory_service):
    engine, factory = database
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_deferred_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'deferred commit failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE CONSTRAINT TRIGGER fail_deferred_test_log
            AFTER INSERT ON memory_logs DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION fail_deferred_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="deferred commit failure"):
            await memory_service.create(256, "GB", uuid4())
        assert await counts(factory) == (0, 0)
        assert engine.sync_engine.pool.checkedout() == 0
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_deferred_test_log ON memory_logs"))
            await session.execute(text("DROP FUNCTION fail_deferred_test_log()"))
            await session.commit()


async def test_concurrent_equivalent_create_has_single_entity_and_log(database, memory_service):
    _, factory = database
    results = await asyncio.gather(
        memory_service.create(1, "TB", uuid4()),
        memory_service.create(1000, "GB", uuid4()),
        return_exceptions=True,
    )
    errors = [result for result in results if isinstance(result, ApplicationError)]
    assert len(errors) == 1 and errors[0].code == "MEMORY_CAPACITY_DUPLICATE"
    assert all(
        not isinstance(result, Exception) or isinstance(result, ApplicationError)
        for result in results
    )
    assert await counts(factory) == (1, 1)


async def test_concurrent_different_rows_same_new_capacity_has_single_update(
    database, memory_service
):
    _, factory = database
    first = await memory_service.create(128, "GB", uuid4())
    second = await memory_service.create(256, "GB", uuid4())
    results = await asyncio.gather(
        memory_service.change_size(first.id, 1, "TB", uuid4()),
        memory_service.change_size(second.id, 1000, "GB", uuid4()),
        return_exceptions=True,
    )
    errors = [result for result in results if isinstance(result, ApplicationError)]
    assert len(errors) == 1 and errors[0].code == "MEMORY_CAPACITY_DUPLICATE"
    assert all(
        not isinstance(result, Exception) or isinstance(result, ApplicationError)
        for result in results
    )
    assert await counts(factory) == (2, 3)
    current = [await memory_service.get(first.id), await memory_service.get(second.id)]
    assert sum(item.capacity * (1000 if item.unit == "TB" else 1) == 1000 for item in current) == 1


async def test_concurrent_updates_preserve_locked_history_chain(database, memory_service):
    _, factory = database
    memory = await memory_service.create(256, "GB", uuid4())
    await asyncio.gather(
        memory_service.change_size(memory.id, 512, "GB", uuid4()),
        memory_service.change_size(memory.id, 1024, "GB", uuid4()),
    )
    history = await logs(factory, memory.id)
    assert [item.operation for item in history] == ["create", "update", "update"]
    assert history[1].before == history[0].after and history[2].before == history[1].after
    assert history[2].after["capacity"] == (await memory_service.get(memory.id)).capacity


@pytest.mark.parametrize(
    ("capacity", "unit", "code"),
    [
        (0, "GB", "0GB"),
        (-1, "GB", "-1GB"),
        (2147483648, "GB", "2147483648GB"),
        (1, "MB", "1MB"),
        (1, "gb", "1gb"),
        (256, "GB", "BAD"),
    ],
)
async def test_database_capacity_unit_code_constraints(database, capacity, unit, code):
    _, factory = database
    async with factory() as session:
        with pytest.raises(DBAPIError) as error:
            await session.execute(
                text(
                    "INSERT INTO memories (id,capacity,unit,code,created_at,updated_at) "
                    "VALUES (:id,:capacity,:unit,:code,now(),now())"
                ),
                {"id": uuid4(), "capacity": capacity, "unit": unit, "code": code},
            )
        assert error.value.orig is not None
        cause = error.value.orig.__cause__
        assert getattr(cause, "sqlstate", None) in {"23514", "22000", "22003"}
        await session.rollback()
    assert await counts(factory) == (0, 0)
