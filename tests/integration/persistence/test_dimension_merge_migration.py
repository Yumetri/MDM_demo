import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

MERGE_REVISION = "0005_merge_brand_country"
LATEST_REVISION = "0009_merge_memory_dimensions"


def migrate(connection: Connection, revision: str, *, downgrade: bool = False) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [LATEST_REVISION]
    head = script.get_revision(LATEST_REVISION)
    assert head is not None and head.down_revision == (
        "0008_merge_dimension_heads",
        "0007_merge_year_memory",
    )
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.mark.parametrize("initial_revision", ["0003", "0004", "0004_country", "both"])
async def test_merge_upgrade_preserves_either_branch_and_existing_logs(database, initial_revision):
    engine, _ = database
    schema = "test_dimension_merge_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            revisions = (
                ("0004", "0004_country") if initial_revision == "both" else (initial_revision,)
            )
            for revision in revisions:
                await connection.run_sync(lambda conn, rev=revision: migrate(conn, rev))
            previous_rows = {}
            dimensions = (
                ("companies", "company_logs", "company_id"),
                ("models", "model_logs", "model_id"),
                ("brands", "brand_logs", "brand_id"),
                ("countries", "country_logs", "country_id"),
            )
            for table, log_table, target_column in dimensions:
                exists = await connection.run_sync(
                    lambda conn, table=table: inspect(conn).has_table(table)
                )
                if not exists:
                    continue
                entity_id = uuid4()
                snapshot = {"id": str(entity_id), "name": "EXISTING", "code": "EXI"}
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id, name, code, created_at, updated_at) "
                        "VALUES (:id, 'EXISTING', 'EXI', now(), now())"
                    ),
                    {"id": entity_id},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {log_table} "
                        f"(id, {target_column}, operation, occurred_at, request_id, before, after) "
                        "VALUES (:log_id, :id, 'create', now(), :request_id, NULL, "
                        "CAST(:snapshot AS jsonb))"
                    ),
                    {
                        "log_id": uuid4(),
                        "id": entity_id,
                        "request_id": uuid4(),
                        "snapshot": json.dumps(snapshot),
                    },
                )
                for name in (table, log_table):
                    previous_rows[name] = (
                        await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                    ).all()
            await connection.run_sync(lambda conn: migrate(conn, MERGE_REVISION))
            assert (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all() == [MERGE_REVISION]
            for table, log_table, _ in dimensions:
                for name in (table, log_table):
                    rows = (
                        await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                    ).all()
                    assert rows == previous_rows.get(name, [])
            # An explicit parent avoids an ambiguous relative walk at a merge point.
            # Downgrading the merge keeps both parent schemas and their data.
            await connection.run_sync(lambda conn: migrate(conn, "0004", downgrade=True))
            assert set(
                (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalars()
            ) == {"0004", "0004_country"}
            for name, expected in previous_rows.items():
                assert (
                    await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                ).all() == expected
            await connection.run_sync(lambda conn: migrate(conn, MERGE_REVISION))
            assert (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all() == [MERGE_REVISION]
        finally:
            await transaction.rollback()
