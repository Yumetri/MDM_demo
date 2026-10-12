from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


def migrate(conn, revision, downgrade=False):
    config = Config("alembic.ini")
    config.attributes["connection"] = conn
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.mark.parametrize("base", ["base", "0005_merge_brand_country"])
async def test_year_migration_preserves_all_dimensions_and_roundtrip(database, base):
    engine, _ = database
    schema = "test_year_migration_" + uuid4().hex
    assert ScriptDirectory.from_config(Config("alembic.ini")).get_heads() == [
        "0008_merge_dimension_heads"
    ]
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            if base != "base":
                await connection.run_sync(lambda conn: migrate(conn, base))
                for table in ["companies", "models", "brands", "countries"]:
                    await connection.execute(
                        text(
                            f"INSERT INTO {table} (id, name, code, created_at, updated_at) "
                            "VALUES (:id, 'EXISTING', 'EXI', now(), now())"
                        ),
                        {"id": uuid4()},
                    )
            before = {}
            if base != "base":
                for table in ["companies", "models", "brands", "countries"]:
                    before[table] = (await connection.execute(text(f"SELECT * FROM {table}"))).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: migrate(conn, "head"))
                for table, rows in before.items():
                    assert (await connection.execute(text(f"SELECT * FROM {table}"))).all() == rows
                for table in ["years", "year_logs"]:
                    assert (
                        await connection.run_sync(
                            lambda conn, table=table: inspect(conn).get_foreign_keys(table)
                        )
                        == []
                    )
                await connection.execute(
                    text(
                        "INSERT INTO years (id, year, code, "
                        "created_at, updated_at) VALUES "
                        "(:id, 2024, '2024', now(), now())"
                    ),
                    {"id": uuid4()},
                )
                await connection.run_sync(
                    lambda conn: migrate(conn, "0005_merge_brand_country", True)
                )
                assert not await connection.run_sync(lambda conn: inspect(conn).has_table("years"))
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("year_logs")
                )
                for table, rows in before.items():
                    assert (await connection.execute(text(f"SELECT * FROM {table}"))).all() == rows
        finally:
            await transaction.rollback()
