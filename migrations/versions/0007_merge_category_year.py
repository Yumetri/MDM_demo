"""Merge Category and Year without changing their existing schemas."""

revision = "0007_merge_category_year"
down_revision = ("0006_category", "0006_year_dimension")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
