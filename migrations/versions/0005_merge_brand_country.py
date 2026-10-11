"""Merge independently deployed Brand and Country migration heads."""

revision = "0005_merge_brand_country"
down_revision = ("0004", "0004_country")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
