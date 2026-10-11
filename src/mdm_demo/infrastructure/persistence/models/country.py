from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mdm_demo.infrastructure.persistence.models.base import Base


class CountryModel(Base):
    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("code", name="uq_countries_code"),
        UniqueConstraint("name", name="uq_countries_name"),
        CheckConstraint("code ~ '^[A-Z]{3}$'", name="ck_countries_code"),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100 AND name = btrim(name)", name="ck_countries_name"
        ),
        Index("ix_countries_created_at_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100, collation="C"))
    code: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
