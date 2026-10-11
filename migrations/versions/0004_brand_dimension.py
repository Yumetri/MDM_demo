"""Brand and append-only dimension audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_brands_code"),
        sa.CheckConstraint("code ~ '^[A-Z0-9]{3}$'", name="ck_brands_code"),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100 AND name = btrim(name)", name="ck_brands_name"
        ),
    )
    op.create_index("ix_brands_created_at_id", "brands", ["created_at", "id"])
    op.create_table(
        "brand_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_brand_logs_operation"
        ),
        sa.CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_brand_logs_snapshots",
        ),
    )
    op.create_index(
        "ix_brand_logs_brand_time",
        "brand_logs",
        ["brand_id", "occurred_at", "id"],
    )
    op.execute("""CREATE FUNCTION reject_brand_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'brand_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER brand_logs_append_only BEFORE UPDATE OR DELETE
        ON brand_logs FOR EACH ROW EXECUTE FUNCTION reject_brand_log_change()""")


def downgrade() -> None:
    op.drop_table("brand_logs")
    op.execute("DROP FUNCTION reject_brand_log_change()")
    op.drop_table("brands")
