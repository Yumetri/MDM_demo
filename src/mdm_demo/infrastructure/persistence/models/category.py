from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mdm_demo.infrastructure.persistence.models.base import Base


class CategoryModel(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("code", name="uq_categories_code"),
        UniqueConstraint("name", name="uq_categories_name"),
        CheckConstraint("code ~ '^[A-Z0-9]{3}$'", name="ck_categories_code"),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100 AND name = btrim(name)", name="ck_categories_name"
        ),
        Index("ix_categories_created_at_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100, collation="C"))
    code: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
