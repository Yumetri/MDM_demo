"""Company and append-only dimension audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_companies_code"),
        sa.CheckConstraint("code ~ '^[A-Z]{3}$'", name="ck_companies_code"),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 200 AND name = btrim(name)", name="ck_companies_name"
        ),
    )
    op.create_index("ix_companies_created_at_id", "companies", ["created_at", "id"])
    op.create_table(
        "dimension_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_dimension_logs_operation"
        ),
        sa.CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_dimension_logs_snapshots",
        ),
    )
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


def downgrade() -> None:
    op.drop_table("dimension_logs")
    op.execute("DROP FUNCTION reject_dimension_log_change()")
    op.drop_table("companies")
