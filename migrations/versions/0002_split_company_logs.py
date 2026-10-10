"""Preserve existing Company audit rows in a dedicated table without foreign keys."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No other dimension has been implemented. Refuse to relabel unknown audit rows.
    op.execute("LOCK TABLE dimension_logs IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM dimension_logs WHERE dimension <> 'company') THEN
            RAISE EXCEPTION 'Cannot migrate non-company dimension logs';
        END IF;
    END; $$""")
    op.execute("DROP TRIGGER dimension_logs_append_only ON dimension_logs")
    op.execute("DROP FUNCTION reject_dimension_log_change()")
    op.drop_index("ix_dimension_logs_target_time", table_name="dimension_logs")
    op.rename_table("dimension_logs", "company_logs")
    op.alter_column("company_logs", "target_id", new_column_name="company_id")
    op.drop_column("company_logs", "dimension")
    op.execute(
        "ALTER TABLE company_logs RENAME CONSTRAINT dimension_logs_pkey TO company_logs_pkey"
    )
    op.execute("""ALTER TABLE company_logs RENAME CONSTRAINT
        ck_dimension_logs_operation TO ck_company_logs_operation""")
    op.execute("""ALTER TABLE company_logs RENAME CONSTRAINT
        ck_dimension_logs_snapshots TO ck_company_logs_snapshots""")
    op.create_index(
        "ix_company_logs_company_time", "company_logs", ["company_id", "occurred_at", "id"]
    )
    op.execute("""CREATE FUNCTION reject_company_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'company_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER company_logs_append_only BEFORE UPDATE OR DELETE
        ON company_logs FOR EACH ROW EXECUTE FUNCTION reject_company_log_change()""")


def downgrade() -> None:
    op.execute("LOCK TABLE company_logs IN ACCESS EXCLUSIVE MODE")
    op.execute("DROP TRIGGER company_logs_append_only ON company_logs")
    op.execute("DROP FUNCTION reject_company_log_change()")
    op.drop_index("ix_company_logs_company_time", table_name="company_logs")
    op.rename_table("company_logs", "dimension_logs")
    op.alter_column("dimension_logs", "company_id", new_column_name="target_id")
    op.add_column(
        "dimension_logs",
        sa.Column("dimension", sa.String(50), nullable=False, server_default="company"),
    )
    op.alter_column("dimension_logs", "dimension", server_default=None)
    op.execute(
        "ALTER TABLE dimension_logs RENAME CONSTRAINT company_logs_pkey TO dimension_logs_pkey"
    )
    op.execute("""ALTER TABLE dimension_logs RENAME CONSTRAINT
        ck_company_logs_operation TO ck_dimension_logs_operation""")
    op.execute("""ALTER TABLE dimension_logs RENAME CONSTRAINT
        ck_company_logs_snapshots TO ck_dimension_logs_snapshots""")
    op.create_index(
        "ix_dimension_logs_target_time",
        "dimension_logs",
        ["dimension", "target_id", "occurred_at", "id"],
    )
    op.execute("""CREATE FUNCTION reject_dimension_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'dimension_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER dimension_logs_append_only BEFORE UPDATE OR DELETE
        ON dimension_logs FOR EACH ROW EXECUTE FUNCTION reject_dimension_log_change()""")
