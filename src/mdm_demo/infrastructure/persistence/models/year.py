from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mdm_demo.infrastructure.persistence.models.base import Base


class YearModel(Base):
    __tablename__ = "years"
    __table_args__ = (
        UniqueConstraint("year", name="uq_years_year"),
        UniqueConstraint("code", name="uq_years_code"),
        CheckConstraint("year BETWEEN 1900 AND 2999", name="ck_years_year"),
        CheckConstraint("code = year::text", name="ck_years_code"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
