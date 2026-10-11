"""Country and append-only dimension audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_country"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100, collation="C"), nullable=False),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_countries_code"),
        sa.UniqueConstraint("name", name="uq_countries_name"),
        sa.CheckConstraint("code ~ '^[A-Z]{3}$'", name="ck_countries_code"),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100 AND name = btrim(name)", name="ck_countries_name"
        ),
    )
    op.create_index("ix_countries_created_at_id", "countries", ["created_at", "id"])
    op.create_table(
        "country_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_country_logs_operation"
        ),
        sa.CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_country_logs_snapshots",
        ),
    )
    op.create_index(
        "ix_country_logs_country_time",
        "country_logs",
        ["country_id", "occurred_at", "id"],
    )
    op.execute("""CREATE FUNCTION reject_country_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'country_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER country_logs_append_only BEFORE UPDATE OR DELETE
        ON country_logs FOR EACH ROW EXECUTE FUNCTION reject_country_log_change()""")


def downgrade() -> None:
    op.drop_table("country_logs")
    op.execute("DROP FUNCTION reject_country_log_change()")
    op.drop_table("countries")
