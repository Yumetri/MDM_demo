import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

MERGE_REVISION = "0007_merge_category_year"
PARENTS = ("0006_category", "0006_year_dimension")


def migrate(connection, revision, *, downgrade=False):
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["0008_merge_dimension_heads"]
    head = script.get_revision(MERGE_REVISION)
    assert head is not None and head.down_revision == PARENTS
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.mark.parametrize("initial", ["base", *PARENTS, "both"])
async def test_category_year_merge_preserves_parent_data_and_logs(database, initial):
    engine, _ = database
    schema = "test_category_year_merge_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            for revision in PARENTS if initial == "both" else (initial,):
                await connection.run_sync(lambda conn, rev=revision: migrate(conn, rev))
            previous = {}
            for table, logs, key, field, value, code in (
                ("categories", "category_logs", "category_id", "name", "EXISTING", "EXI"),
                ("years", "year_logs", "year_id", "year", 2024, "2024"),
            ):
                if not await connection.run_sync(
                    lambda conn, table=table: inspect(conn).has_table(table)
                ):
                    continue
                entity_id = uuid4()
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id,{field},code,created_at,updated_at) "
                        "VALUES (:id,:value,:code,now(),now())"
                    ),
                    {"id": entity_id, "value": value, "code": code},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {logs} "
                        f"(id,{key},operation,occurred_at,request_id,before,after) "
                        "VALUES (:log,:id,'create',now(),:request,NULL,CAST(:snapshot AS jsonb))"
                    ),
                    {
                        "log": uuid4(),
                        "id": entity_id,
                        "request": uuid4(),
                        "snapshot": json.dumps({"id": str(entity_id), field: value, "code": code}),
                    },
                )
                for name in (table, logs):
                    previous[name] = (
                        await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                    ).all()
            await connection.run_sync(lambda conn: migrate(conn, MERGE_REVISION))
            assert (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all() == [MERGE_REVISION]
            for table in ("categories", "category_logs", "years", "year_logs"):
                assert (
                    await connection.execute(text(f"SELECT * FROM {table} ORDER BY id"))
                ).all() == previous.get(table, [])
            # Remove only the merge node, leaving both parent schemas and records intact.
            await connection.run_sync(lambda conn: migrate(conn, PARENTS[0], downgrade=True))
            assert set(
                (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalars()
            ) == set(PARENTS)
            for name, rows in previous.items():
                assert (
                    await connection.execute(text(f"SELECT * FROM {name} ORDER BY id"))
                ).all() == rows
            await connection.run_sync(lambda conn: migrate(conn, MERGE_REVISION))
            assert (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all() == [MERGE_REVISION]
        finally:
            await transaction.rollback()
