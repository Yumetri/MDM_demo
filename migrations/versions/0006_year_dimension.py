"""Year and append-only dimension audit history."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_year_dimension"
down_revision = "0005_merge_brand_country"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "years",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("year", name="uq_years_year"),
        sa.UniqueConstraint("code", name="uq_years_code"),
        sa.CheckConstraint("year BETWEEN 1900 AND 2999", name="ck_years_year"),
        sa.CheckConstraint("code = year::text", name="ck_years_code"),
    )
    op.create_table(
        "year_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("year_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("before", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("after", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_year_logs_operation"
        ),
        sa.CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_year_logs_snapshots",
        ),
    )
    op.create_index(
        "ix_year_logs_year_time",
        "year_logs",
        ["year_id", "occurred_at", "id"],
    )
    op.execute("""CREATE FUNCTION reject_year_log_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'year_logs is append-only' USING ERRCODE = '23514';
        END; $$""")
    op.execute("""CREATE TRIGGER year_logs_append_only BEFORE UPDATE OR DELETE
        ON year_logs FOR EACH ROW EXECUTE FUNCTION reject_year_log_change()""")


def downgrade() -> None:
    op.drop_table("year_logs")
    op.execute("DROP FUNCTION reject_year_log_change()")
    op.drop_table("years")
