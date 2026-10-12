"""Merge independently applied Year and Memory migration heads."""

revision = "0007_merge_year_memory"
down_revision = ("0006_year_dimension", "0006_memory")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
