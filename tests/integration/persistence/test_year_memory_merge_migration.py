import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


@pytest.mark.parametrize("initial", ["0006_year_dimension", "0006_memory", "both"])
async def test_year_memory_merge_preserves_each_deployed_head_and_logs(database, initial):
    engine, _ = database
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["0007_merge_year_memory"]
    for revision in ("0006_year_dimension", "0006_memory"):
        node = script.get_revision(revision)
        assert node is not None and node.down_revision == "0005_merge_brand_country"
    schema = "test_year_memory_merge_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

            def migrate(conn, revision, downgrade=False):
                config.attributes["connection"] = conn
                (command.downgrade if downgrade else command.upgrade)(config, revision)

            parents = ("0006_year_dimension", "0006_memory") if initial == "both" else (initial,)
            for parent in parents:
                await connection.run_sync(lambda conn, parent=parent: migrate(conn, parent))
            before = {}
            for dimension, table, fields, snapshot in [
                ("year", "years", "year,code", {"year": 2024, "code": "2024"}),
                (
                    "memory",
                    "memories",
                    "capacity,unit,code",
                    {"capacity": 1, "unit": "TB", "code": "1TB"},
                ),
            ]:
                if not await connection.run_sync(
                    lambda conn, table=table: inspect(conn).has_table(table)
                ):
                    continue
                identity = uuid4()
                values = ",".join(":" + field for field in fields.split(","))
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id,{fields},created_at,updated_at) "
                        f"VALUES (:id,{values},now(),now())"
                    ),
                    {"id": identity, **snapshot},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {dimension}_logs "
                        f"(id,{dimension}_id,operation,occurred_at,request_id,before,after) "
                        "VALUES (:log,:id,'create',now(),:request,NULL,CAST(:snapshot AS jsonb))"
                    ),
                    {
                        "log": uuid4(),
                        "id": identity,
                        "request": uuid4(),
                        "snapshot": json.dumps({"id": str(identity), **snapshot}),
                    },
                )
                for name in [table, dimension + "_logs"]:
                    before[name] = (await connection.execute(text(f"SELECT * FROM {name}"))).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: migrate(conn, "head"))
                assert (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalars().all() == ["0007_merge_year_memory"]
                for table in ["years", "year_logs", "memories", "memory_logs"]:
                    assert await connection.run_sync(
                        lambda conn, table=table: inspect(conn).has_table(table)
                    )
                    assert (
                        await connection.execute(text(f"SELECT * FROM {table}"))
                    ).all() == before.get(table, [])
                # Removing only the merge node retains both applied parent schemas.
                await connection.run_sync(lambda conn: migrate(conn, "0006_memory", True))
                assert set(
                    (
                        await connection.execute(text("SELECT version_num FROM alembic_version"))
                    ).scalars()
                ) == {"0006_year_dimension", "0006_memory"}
                for table in ["years", "year_logs", "memories", "memory_logs"]:
                    assert (
                        await connection.execute(text(f"SELECT * FROM {table}"))
                    ).all() == before.get(table, [])
        finally:
            await transaction.rollback()
