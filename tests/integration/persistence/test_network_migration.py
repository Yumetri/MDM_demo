from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text


async def test_network_migration_preserves_all_existing_dimensions(database):
    engine, _ = database
    config = Config("alembic.ini")
    assert ScriptDirectory.from_config(config).get_heads() == ["0008_merge_dimension_heads"]
    schema = "test_network_migration_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

            def migrate(conn, revision, downgrade=False):
                config.attributes["connection"] = conn
                if downgrade:
                    command.downgrade(config, revision)
                else:
                    command.upgrade(config, revision)

            await connection.run_sync(lambda conn: migrate(conn, "0005_merge_brand_country"))
            collections = [
                ("companies", "company_logs", "company_id"),
                ("models", "model_logs", "model_id"),
                ("brands", "brand_logs", "brand_id"),
                ("countries", "country_logs", "country_id"),
            ]
            saved = {}
            for table, log_table, id_field in collections:
                entity_id = uuid4()
                await connection.execute(
                    text(
                        f"INSERT INTO {table} (id,name,code,created_at,updated_at) "
                        "VALUES (:id,'EXISTING','EXI',now(),now())"
                    ),
                    {"id": entity_id},
                )
                await connection.execute(
                    text(
                        f"INSERT INTO {log_table} "
                        f"(id,{id_field},operation,occurred_at,request_id,before,after) "
                        "VALUES (:log,:id,'create',now(),:request,NULL,"
                        "jsonb_build_object('id',CAST(CAST(:id AS uuid) AS text),"
                        "'name','EXISTING','code','EXI'))"
                    ),
                    {"log": uuid4(), "id": entity_id, "request": uuid4()},
                )
                for target in [table, log_table]:
                    saved[target] = (
                        await connection.execute(text(f"SELECT * FROM {target}"))
                    ).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: migrate(conn, "0006_network"))
                for table, expected in saved.items():
                    assert (
                        await connection.execute(text(f"SELECT * FROM {table}"))
                    ).all() == expected
                for table in ["networks", "network_logs"]:
                    assert (
                        await connection.run_sync(
                            lambda conn, table=table: inspect(conn).get_foreign_keys(table)
                        )
                        == []
                    )
                assert (
                    await connection.execute(text("SELECT count(*) FROM networks"))
                ).scalar() == 0
                await connection.run_sync(
                    lambda conn: migrate(conn, "0005_merge_brand_country", True)
                )
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("networks")
                )
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("network_logs")
                )
        finally:
            await transaction.rollback()
