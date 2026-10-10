import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection


def migrate(connection: Connection, revision: str, *, downgrade: bool = False) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.fixture
async def legacy_schema(database) -> AsyncIterator[AsyncConnection]:
    engine, _ = database
    # A private schema in the isolated test DB; roll back the entire fixture on exit.
    schema = "test_log_migration_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(lambda conn: migrate(conn, "0001"))
            yield connection
        finally:
            await transaction.rollback()


async def test_split_migration_preserves_deleted_company_history_and_round_trip(legacy_schema):
    connection = legacy_schema
    company_id = uuid4()
    before = {"id": str(company_id), "name": "Before", "code": "ABC"}
    after = {**before, "name": "After"}
    for operation, old, new in [
        ("create", None, before),
        ("update", before, after),
        ("delete", after, None),
    ]:
        await connection.execute(
            text("""INSERT INTO dimension_logs
            (id, dimension, target_id, operation, occurred_at, request_id, before, after)
            VALUES (:id, 'company', :target_id, :operation, :occurred_at, :request_id,
                    CAST(:before AS jsonb), CAST(:after AS jsonb))"""),
            {
                "id": uuid4(),
                "target_id": company_id,
                "operation": operation,
                "occurred_at": datetime.now(UTC),
                "request_id": uuid4(),
                "before": json.dumps(old) if old is not None else None,
                "after": json.dumps(new) if new is not None else None,
            },
        )
    original = (
        await connection.execute(
            text("""SELECT id, target_id, operation, occurred_at,
        request_id, before, after FROM dimension_logs ORDER BY id""")
        )
    ).all()
    await connection.run_sync(lambda conn: migrate(conn, "head"))
    migrated = (
        await connection.execute(
            text("""SELECT id, company_id, operation, occurred_at,
        request_id, before, after FROM company_logs ORDER BY id""")
        )
    ).all()
    assert migrated == original
    assert await connection.scalar(text("SELECT count(*) FROM companies")) == 0
    foreign_keys = await connection.run_sync(
        lambda conn: inspect(conn).get_foreign_keys("company_logs")
    )
    assert foreign_keys == []
    columns = await connection.run_sync(lambda conn: inspect(conn).get_columns("company_logs"))
    assert {column["name"] for column in columns} == {
        "id",
        "company_id",
        "operation",
        "occurred_at",
        "request_id",
        "before",
        "after",
    }
    assert next(column for column in columns if column["name"] == "company_id")["nullable"] is False
    indexes = await connection.run_sync(lambda conn: inspect(conn).get_indexes("company_logs"))
    assert any(index["column_names"] == ["company_id", "occurred_at", "id"] for index in indexes)
    assert not await connection.run_sync(lambda conn: inspect(conn).has_table("dimension_logs"))
    with pytest.raises(IntegrityError, match="append-only"):
        async with connection.begin_nested():
            await connection.execute(text("DELETE FROM company_logs"))
    await connection.run_sync(lambda conn: migrate(conn, "0001", downgrade=True))
    restored = (
        await connection.execute(
            text("""SELECT id, target_id, operation, occurred_at,
        request_id, before, after FROM dimension_logs ORDER BY id""")
        )
    ).all()
    assert restored == original
    assert (
        await connection.scalar(
            text("SELECT count(*) FROM dimension_logs WHERE dimension = 'company'")
        )
        == 3
    )
    with pytest.raises(IntegrityError, match="append-only"):
        async with connection.begin_nested():
            await connection.execute(text("DELETE FROM dimension_logs"))
    # A second upgrade must also work without duplicate functions or constraints.
    await connection.run_sync(lambda conn: migrate(conn, "head"))
    assert await connection.scalar(text("SELECT count(*) FROM company_logs")) == 3


async def test_split_refuses_to_relabel_other_dimensions(legacy_schema):
    connection = legacy_schema
    await connection.execute(
        text("""INSERT INTO dimension_logs
        (id, dimension, target_id, operation, occurred_at, request_id, before, after)
        VALUES (:id, 'model', :target, 'create', :at, :request, NULL, '{}')"""),
        {"id": uuid4(), "target": uuid4(), "at": datetime.now(UTC), "request": uuid4()},
    )
    with pytest.raises(DBAPIError, match="non-company"):
        async with connection.begin_nested():
            await connection.run_sync(lambda conn: migrate(conn, "head"))
    assert (
        await connection.scalar(
            text("SELECT count(*) FROM dimension_logs WHERE dimension = 'model'")
        )
        == 1
    )
    assert not await connection.run_sync(lambda conn: inspect(conn).has_table("company_logs"))
    assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
