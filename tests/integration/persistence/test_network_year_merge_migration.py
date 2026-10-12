import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


@pytest.mark.parametrize(
    "initial",
    [
        "base",
        "0006_network",
        "0006_year_dimension",
        "0007_merge_network_year",
        "0006_category",
        "0007_merge_category_year",
        "both",
        "all",
    ],
)
async def test_network_year_merge_preserves_each_head_and_audit_history(database, initial):
    engine, _ = database
    config = Config("alembic.ini")
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["0009_merge_memory_dimensions"]
    head = scripts.get_revision("0007_merge_network_year")
    assert head is not None and isinstance(head.down_revision, tuple)
    assert set(head.down_revision) == {"0006_network", "0006_year_dimension"}
    schema = "test_network_year_merge_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            config.attributes["connection"] = connection.sync_connection
            revisions = ("0006_network", "0006_year_dimension") if initial == "both" else (initial,)
            if initial == "all":
                revisions = ("0007_merge_network_year", "0007_merge_category_year")
            for revision in revisions:
                if revision != "base":
                    await connection.run_sync(
                        lambda conn, rev=revision: command.upgrade(config, rev)
                    )
            preserved = {}
            for table, log_table, target_column, values in [
                ("networks", "network_logs", "network_id", {"name": "EXISTING", "code": "EXI"}),
                ("years", "year_logs", "year_id", {"year": 2024, "code": "2024"}),
                ("categories", "category_logs", "category_id", {"name": "EXISTING", "code": "EXI"}),
            ]:
                if not await connection.run_sync(
                    lambda conn, table=table: inspect(conn).has_table(table)
                ):
                    continue
                entity_id = uuid4()
                value_field = "year" if table == "years" else "name"
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id,{value_field},code,created_at,updated_at) "
                        f"VALUES (:id,:{value_field},:code,now(),now())"
                    ),
                    {"id": entity_id, **values},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {log_table} "
                        f"(id,{target_column},operation,occurred_at,request_id,before,after) "
                        "VALUES (:log_id,:id,'create',now(),:request_id,NULL,"
                        "CAST(:snapshot AS jsonb))"
                    ),
                    {
                        "log_id": uuid4(),
                        "id": entity_id,
                        "request_id": uuid4(),
                        "snapshot": json.dumps({"id": str(entity_id), **values}),
                    },
                )
                for target in (table, log_table):
                    preserved[target] = (
                        await connection.execute(text(f"SELECT * FROM {target} ORDER BY id"))
                    ).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: command.upgrade(config, "head"))
                assert (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalars().all() == ["0009_merge_memory_dimensions"]
                for table in (
                    "networks",
                    "network_logs",
                    "years",
                    "year_logs",
                    "categories",
                    "category_logs",
                ):
                    assert (
                        await connection.execute(text(f"SELECT * FROM {table} ORDER BY id"))
                    ).all() == preserved.get(table, [])
        finally:
            await transaction.rollback()
