import json
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def migrate(connection: Connection, revision: str, *, downgrade: bool = False) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    assert ScriptDirectory.from_config(config).get_heads() == ["0007_merge_year_memory"]
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


@pytest.mark.parametrize(
    "initial", ["base", "0003", "0004", "0004_country", "0005_merge_brand_country"]
)
async def test_memory_migration_empty_and_existing_database_preserves_all_dimensions(
    database, initial
):
    engine, _ = database
    schema = "test_memory_migration_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            if initial != "base":
                await connection.run_sync(lambda conn: migrate(conn, initial))
            snapshots = {}
            if initial != "base":
                for dimension, table in [
                    ("company", "companies"),
                    ("model", "models"),
                    ("brand", "brands"),
                    ("country", "countries"),
                ]:
                    if not await connection.run_sync(
                        lambda conn, table=table: inspect(conn).has_table(table)
                    ):
                        continue
                    identity = uuid4()
                    await connection.execute(
                        text(
                            f"INSERT INTO {table} (id,name,code,created_at,updated_at) "
                            "VALUES (:id,'EXISTING','EXI',now(),now())"
                        ),
                        {"id": identity},
                    )
                    await connection.execute(
                        text(
                            f"INSERT INTO {dimension}_logs "
                            f"(id,{dimension}_id,operation,occurred_at,request_id,before,after) "
                            "VALUES(:log,:id,'create',now(),:request,NULL,CAST(:snapshot AS jsonb))"
                        ),
                        {
                            "log": uuid4(),
                            "id": identity,
                            "request": uuid4(),
                            "snapshot": json.dumps(
                                {"id": str(identity), "name": "EXISTING", "code": "EXI"}
                            ),
                        },
                    )
                    for name in [table, f"{dimension}_logs"]:
                        snapshots[name] = (
                            await connection.execute(text(f"SELECT * FROM {name}"))
                        ).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: migrate(conn, "0006_memory"))
                assert (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar() == "0006_memory"
                for name, expected in snapshots.items():
                    assert (
                        await connection.execute(text(f"SELECT * FROM {name}"))
                    ).all() == expected
                for table in ["memories", "memory_logs"]:
                    assert (
                        await connection.run_sync(
                            lambda conn, table=table: inspect(conn).get_foreign_keys(table)
                        )
                        == []
                    )
                columns = await connection.run_sync(
                    lambda conn: inspect(conn).get_columns("memories")
                )
                computed = next(column for column in columns if column["name"] == "capacity_gb")
                assert computed["computed"]["persisted"] is True
                identity = uuid4()
                await connection.execute(
                    text(
                        "INSERT INTO memories (id,capacity,unit,code,created_at,updated_at) "
                        "VALUES (:id,2147483647,'TB','2147483647TB',now(),now())"
                    ),
                    {"id": identity},
                )
                assert (
                    await connection.execute(
                        text("SELECT capacity_gb FROM memories WHERE id=:id"), {"id": identity}
                    )
                ).scalar() == 2147483647000
                await connection.run_sync(
                    lambda conn: migrate(conn, "0005_merge_brand_country", downgrade=True)
                )
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("memories")
                )
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("memory_logs")
                )
                for name, expected in snapshots.items():
                    assert (
                        await connection.execute(text(f"SELECT * FROM {name}"))
                    ).all() == expected
        finally:
            await transaction.rollback()
