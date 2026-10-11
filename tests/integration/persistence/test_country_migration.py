from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def migrate(connection: Connection, revision: str, *, downgrade: bool = False) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    if downgrade:
        command.downgrade(config, revision)
    else:
        command.upgrade(config, revision)


async def test_country_migration_keeps_company_data_and_supports_roundtrip(database):
    engine, _ = database
    schema = "test_country_migration_" + uuid4().hex
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(lambda conn: migrate(conn, "0003"))
            company_id = uuid4()
            await connection.execute(
                text("""INSERT INTO companies (id, name, code, created_at, updated_at)
                VALUES (:id, 'Existing', 'EXI', now(), now())"""),
                {"id": company_id},
            )
            await connection.execute(
                text("""INSERT INTO company_logs
                (id, company_id, operation, occurred_at, request_id, before, after)
                VALUES (:log, :id, 'create', now(), :request, NULL,
                jsonb_build_object('id', CAST(CAST(:id AS uuid) AS text),
                'name', 'Existing', 'code', 'EXI'))"""),
                {"log": uuid4(), "id": company_id, "request": uuid4()},
            )
            await connection.execute(
                text(
                    "INSERT INTO models (id,name,code,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),'Existing Model','EXM',now(),now())"
                )
            )
            models = (await connection.execute(text("SELECT * FROM models"))).all()
            company = (await connection.execute(text("SELECT * FROM companies"))).all()
            history = (await connection.execute(text("SELECT * FROM company_logs"))).all()
            for _ in range(2):
                await connection.run_sync(lambda conn: migrate(conn, "0004_country"))
                assert (await connection.execute(text("SELECT * FROM companies"))).all() == company
                assert (
                    await connection.execute(text("SELECT * FROM company_logs"))
                ).all() == history
                assert (await connection.execute(text("SELECT * FROM models"))).all() == models
                for table in ("countries", "country_logs"):
                    assert (
                        await connection.run_sync(
                            lambda conn, table=table: inspect(conn).get_foreign_keys(table)
                        )
                        == []
                    )
                columns = await connection.run_sync(
                    lambda conn: inspect(conn).get_columns("country_logs")
                )
                assert {column["name"] for column in columns} == {
                    "id",
                    "country_id",
                    "operation",
                    "occurred_at",
                    "request_id",
                    "before",
                    "after",
                }
                assert not next(c for c in columns if c["name"] == "country_id")["nullable"]
                indexes = await connection.run_sync(
                    lambda conn: inspect(conn).get_indexes("country_logs")
                )
                assert any(
                    i["column_names"] == ["country_id", "occurred_at", "id"] for i in indexes
                )
                await connection.run_sync(lambda conn: migrate(conn, "0003", downgrade=True))
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("countries")
                )
                assert not await connection.run_sync(
                    lambda conn: inspect(conn).has_table("country_logs")
                )
                assert (
                    await connection.execute(text("SELECT * FROM company_logs"))
                ).all() == history
        finally:
            await transaction.rollback()
