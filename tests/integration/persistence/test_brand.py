import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mdm_demo.application.errors import ApplicationError
from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.domain.entities.brand import Brand
from mdm_demo.domain.entities.brand_log import BrandLog
from mdm_demo.domain.value_objects.brand_code import BrandCode
from mdm_demo.domain.value_objects.brand_name import BrandName
from mdm_demo.infrastructure.persistence.mappers import brand_log_mapper, brand_mapper
from mdm_demo.infrastructure.persistence.models.brand import BrandModel
from mdm_demo.infrastructure.persistence.models.brand_log import BrandLogModel
from mdm_demo.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


async def counts(factory):
    async with factory() as session:
        return (
            await session.scalar(select(func.count()).select_from(BrandModel)),
            await session.scalar(select(func.count()).select_from(BrandLogModel)),
        )


async def logs(factory, brand_id):
    async with factory() as session:
        return list(
            await session.scalars(
                select(BrandLogModel)
                .where(BrandLogModel.brand_id == brand_id)
                .order_by(BrandLogModel.occurred_at, BrandLogModel.id)
            )
        )


async def test_mapper_roundtrip_and_commit(database):
    _, factory = database
    brand = Brand.create(" 삼성  전자 ", "abc")
    log = BrandLog.record(brand.id, "create", uuid4(), None, brand.snapshot())
    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.brands.add(brand)
        await uow.brand_logs.add(log)
        await uow.commit()
    async with factory() as session:
        row = await session.get(BrandModel, brand.id)
        log_row = await session.get(BrandLogModel, log.id)
        assert row is not None and log_row is not None
        restored = brand_mapper.to_domain(row)
        restored_log = brand_log_mapper.to_domain(log_row)
        assert restored.snapshot() == brand.snapshot()
        assert restored.created_at == brand.created_at
        assert restored.updated_at == brand.updated_at
        assert restored_log == log
        assert restored_log.before is None and restored_log.after == log.after
        assert restored_log.request_id == log.request_id
        assert restored_log.occurred_at == log.occurred_at


@pytest.mark.parametrize("raise_error", [False, True])
async def test_uncommitted_exit_rolls_back_both(database, raise_error):
    _, factory = database
    try:
        async with SqlAlchemyUnitOfWork(factory) as uow:
            brand = Brand.create("Samsung")
            await uow.brands.add(brand)
            await uow.brand_logs.add(
                BrandLog.record(brand.id, "create", uuid4(), None, brand.snapshot())
            )
            if raise_error:
                raise RuntimeError("business operation failed")
    except RuntimeError:
        pass
    assert await counts(factory) == (0, 0)


@pytest.mark.parametrize("operation", ["create", "rename", "delete"])
async def test_log_database_failure_rolls_back_brand(database, brand_service, operation):
    _, factory = database
    initial = (
        await brand_service.create("Samsung", None, uuid4()) if operation != "create" else None
    )
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test injected failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE TRIGGER fail_test_log BEFORE INSERT ON brand_logs
            FOR EACH ROW EXECUTE FUNCTION fail_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="test injected failure"):
            if initial is None:
                await brand_service.create("Samsung", None, uuid4())
            elif operation == "rename":
                await brand_service.rename(initial.id, "Changed", uuid4())
            else:
                await brand_service.delete(initial.id, uuid4())
        assert await counts(factory) == ((0, 0) if initial is None else (1, 1))
        if initial is not None:
            assert (await brand_service.get(initial.id)).name == "Samsung"
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_test_log ON brand_logs"))
            await session.execute(text("DROP FUNCTION fail_test_log()"))
            await session.commit()


async def test_commit_failure_cleans_up(database, brand_cursor_codec):
    engine, factory = database

    class FailingSession(AsyncSession):
        async def commit(self) -> None:
            raise RuntimeError("injected before commit")

    failing_factory = async_sessionmaker(engine, class_=FailingSession, expire_on_commit=False)
    brand_service = BrandUseCases(lambda: SqlAlchemyUnitOfWork(failing_factory), brand_cursor_codec)
    with pytest.raises(RuntimeError, match="injected before commit"):
        await brand_service.create("Samsung", None, uuid4())
    assert await counts(factory) == (0, 0)
    assert engine.sync_engine.pool.checkedout() == 0


async def test_cancellation_during_commit_cleans_up(database, brand_cursor_codec):
    engine, factory = database
    entered = asyncio.Event()

    class WaitingSession(AsyncSession):
        async def commit(self) -> None:
            entered.set()
            await asyncio.Event().wait()

    waiting_factory = async_sessionmaker(engine, class_=WaitingSession, expire_on_commit=False)
    brand_service = BrandUseCases(lambda: SqlAlchemyUnitOfWork(waiting_factory), brand_cursor_codec)
    task = asyncio.create_task(brand_service.create("Samsung", None, uuid4()))
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
        async with SqlAlchemyUnitOfWork(slow_factory) as uow:
            await uow.brands.add(Brand.create("Samsung"))

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


async def test_concurrent_create_unique_code_and_single_log(database, brand_service):
    _, factory = database
    results = await asyncio.gather(
        brand_service.create("Samsung", None, uuid4()),
        brand_service.create("Samson", "sam", uuid4()),
        return_exceptions=True,
    )
    failures = [result for result in results if isinstance(result, ApplicationError)]
    assert len(failures) == 1
    assert failures[0].code in {"BRAND_CODE_DUPLICATE", "DIMENSION_AUTO_CODE_DUPLICATE"}
    assert await counts(factory) == (1, 1)


async def test_concurrent_renames_preserve_history_chain(database, brand_service):
    _, factory = database
    brand = await brand_service.create("Samsung", None, uuid4())
    await asyncio.gather(
        brand_service.rename(brand.id, "Name A", uuid4()),
        brand_service.rename(brand.id, "Name B", uuid4()),
    )
    history = await logs(factory, brand.id)
    assert [item.operation for item in history] == ["create", "update", "update"]
    assert history[1].before == history[0].after
    assert history[2].before == history[1].after
    assert history[2].after["name"] == (await brand_service.get(brand.id)).name


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


async def test_update_delete_race_logs_locked_current_value(database, brand_service):
    _, factory = database
    brand = await brand_service.create("Samsung", None, uuid4())
    async with SqlAlchemyUnitOfWork(factory) as uow:
        entity = await uow.brands.get(brand.id, for_update=True)
        assert entity is not None
        before = entity.snapshot()
        entity.rename("Updated before delete")
        await uow.brands.save(entity)
        await uow.brand_logs.add(
            BrandLog.record(entity.id, "update", uuid4(), before, entity.snapshot())
        )
        delete_task = asyncio.create_task(brand_service.delete(brand.id, uuid4()))
        try:
            await wait_for_lock_waiter(factory)
            await uow.commit()
        except BaseException:
            delete_task.cancel()
            await asyncio.gather(delete_task, return_exceptions=True)
            raise
    await asyncio.wait_for(delete_task, 5)
    history = await logs(factory, brand.id)
    assert history[-1].operation == "delete"
    assert history[-1].before == history[-2].after
    assert history[-1].after is None
    assert await counts(factory) == (0, 3)


async def test_delete_then_update_waiter_returns_not_found(database, brand_service):
    _, factory = database
    brand = await brand_service.create("Samsung", None, uuid4())
    async with SqlAlchemyUnitOfWork(factory) as uow:
        entity = await uow.brands.get(brand.id, for_update=True)
        assert entity is not None
        await uow.brands.delete(entity)
        await uow.brand_logs.add(
            BrandLog.record(entity.id, "delete", uuid4(), entity.snapshot(), None)
        )
        rename_task = asyncio.create_task(brand_service.rename(brand.id, "Too late", uuid4()))
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


async def test_append_only_log_and_unrelated_constraint_not_duplicate(database, brand_service):
    _, factory = database
    brand = await brand_service.create("Samsung", None, uuid4())
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text("DELETE FROM brand_logs"))
        await session.rollback()
        with pytest.raises(IntegrityError):
            await session.execute(text("UPDATE brand_logs SET operation = operation"))
        await session.rollback()
    # A duplicate primary key must not be misreported as duplicate brand code.
    async with SqlAlchemyUnitOfWork(factory) as uow:
        existing = await uow.brands.get(brand.id)
        assert existing is not None
        with pytest.raises(IntegrityError):
            await uow.brands.add(existing)


async def test_cursor_same_timestamp_and_deleted_boundary(database, brand_service):
    _, factory = database
    now = datetime.now(UTC)
    entities = [
        Brand(UUID(int=i), BrandName("Same"), BrandCode(code), now, now)
        for i, code in enumerate(["AAA", "AAB", "AAC"], 1)
    ]
    async with SqlAlchemyUnitOfWork(factory) as uow:
        for entity in entities:
            await uow.brands.add(entity)
        await uow.commit()
    first = await brand_service.list(None, 1)
    assert first.items[0].id == UUID(int=1) and first.has_next
    await brand_service.delete(first.items[0].id, uuid4())
    second = await brand_service.list(first.next_cursor, 1)
    third = await brand_service.list(second.next_cursor, 1)
    assert second.items[0].id == UUID(int=2)
    assert third.items[0].id == UUID(int=3)
    assert third.next_cursor is None and not third.has_next


async def test_database_rejects_commit_and_rolls_back_both(database, brand_service):
    engine, factory = database
    async with factory() as session:
        await session.execute(
            text("""CREATE FUNCTION fail_deferred_test_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'deferred commit failure'; END; $$""")
        )
        await session.execute(
            text("""CREATE CONSTRAINT TRIGGER fail_deferred_test_log
            AFTER INSERT ON brand_logs DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION fail_deferred_test_log()""")
        )
        await session.commit()
    try:
        with pytest.raises(Exception, match="deferred commit failure"):
            await brand_service.create("Samsung", None, uuid4())
        assert await counts(factory) == (0, 0)
        assert engine.sync_engine.pool.checkedout() == 0
    finally:
        async with factory() as session:
            await session.execute(text("DROP TRIGGER fail_deferred_test_log ON brand_logs"))
            await session.execute(text("DROP FUNCTION fail_deferred_test_log()"))
            await session.commit()
