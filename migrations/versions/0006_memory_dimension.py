"""Memory capacity and append-only audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_memory"
down_revision = "0005_merge_brand_country"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(2), nullable=False),
        sa.Column("code", sa.String(12), nullable=False),
        sa.Column(
            "capacity_gb",
            sa.BigInteger(),
            sa.Computed(
                "CASE WHEN unit = 'TB' THEN capacity::bigint * 1000 ELSE capacity::bigint END",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_memories_code"),
        sa.UniqueConstraint("capacity_gb", name="uq_memories_capacity_gb"),
        sa.CheckConstraint("capacity BETWEEN 1 AND 2147483647", name="ck_memories_capacity"),
        sa.CheckConstraint("unit IN ('GB', 'TB')", name="ck_memories_unit"),
        sa.CheckConstraint("code = capacity::text || unit", name="ck_memories_code"),
    )
    op.create_index("ix_memories_created_at_id", "memories", ["created_at", "id"])
    op.create_table(
        "memory_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_memory_logs_operation"
        ),
        sa.CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_memory_logs_snapshots",
        ),
    )
    op.create_index("ix_memory_logs_memory_time", "memory_logs", ["memory_id", "occurred_at", "id"])
    op.execute("""CREATE FUNCTION reject_memory_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'memory_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER memory_logs_append_only BEFORE UPDATE OR DELETE
        ON memory_logs FOR EACH ROW EXECUTE FUNCTION reject_memory_log_change()""")


def downgrade() -> None:
    op.drop_table("memory_logs")
    op.execute("DROP FUNCTION reject_memory_log_change()")
    op.drop_table("memories")
