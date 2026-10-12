import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


def migrate(connection, revision, *, downgrade=False):
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    assert ScriptDirectory.from_config(config).get_heads() == ["0006_category"]
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.mark.parametrize("initial", ["base", "0004", "0004_country", "0005_merge_brand_country"])
async def test_category_upgrade_from_existing_heads_and_roundtrip(database, initial):
    engine, _ = database
    schema = "test_category_migration_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(lambda conn: migrate(conn, initial))
            previous = {}
            dimensions = [
                ("companies", "company_logs", "company_id"),
                ("models", "model_logs", "model_id"),
                ("brands", "brand_logs", "brand_id"),
                ("countries", "country_logs", "country_id"),
            ]
            for table, logs, key in dimensions:
                if not await connection.run_sync(
                    lambda conn, table=table: inspect(conn).has_table(table)
                ):
                    continue
                entity_id = uuid4()
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id,name,code,created_at,updated_at) VALUES "
                        "(:id,'EXISTING','EXI',now(),now())"
                    ),
                    {"id": entity_id},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {logs} "
                        f"(id,{key},operation,occurred_at,request_id,before,after) VALUES "
                        "(:log,:id,'create',now(),:request,NULL,CAST(:snapshot AS jsonb))"
                    ),
                    {
                        "log": uuid4(),
                        "id": entity_id,
                        "request": uuid4(),
                        "snapshot": json.dumps(
                            {"id": str(entity_id), "name": "EXISTING", "code": "EXI"}
                        ),
                    },
                )
                for name in (table, logs):
                    previous[name] = (
                        await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                    ).all()
            await connection.run_sync(lambda conn: migrate(conn, "head"))
            assert (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all() == ["0006_category"]
            for name, expected in previous.items():
                assert (
                    await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                ).all() == expected
            for table in ("categories", "category_logs"):
                assert (
                    await connection.run_sync(
                        lambda conn, table=table: inspect(conn).get_foreign_keys(table)
                    )
                    == []
                )
            unique = await connection.run_sync(
                lambda conn: inspect(conn).get_unique_constraints("categories")
            )
            assert {tuple(item["column_names"]) for item in unique} == {("name",), ("code",)}
            indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("category_logs")
            )
            assert any(
                item["column_names"] == ["category_id", "occurred_at", "id"] for item in indexes
            )
            entity = uuid4()
            await connection.execute(
                text(
                    "INSERT INTO categories (id,name,code,created_at,updated_at) VALUES "
                    "(:id,'NOTEBOOK','N01',now(),now())"
                ),
                {"id": entity},
            )
            await connection.run_sync(
                lambda conn: migrate(conn, "0005_merge_brand_country", downgrade=True)
            )
            assert not await connection.run_sync(lambda conn: inspect(conn).has_table("categories"))
            assert not await connection.run_sync(
                lambda conn: inspect(conn).has_table("category_logs")
            )
            for name, expected in previous.items():
                assert (
                    await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                ).all() == expected
            await connection.run_sync(lambda conn: migrate(conn, "head"))
            assert await connection.scalar(text("SELECT count(*) FROM categories")) == 0
        finally:
            await transaction.rollback()
