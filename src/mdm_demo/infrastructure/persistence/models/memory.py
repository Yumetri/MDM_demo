from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from mdm_demo.infrastructure.persistence.models.base import Base


class MemoryModel(Base):
    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint("code", name="uq_memories_code"),
        UniqueConstraint("capacity_gb", name="uq_memories_capacity_gb"),
        CheckConstraint("capacity BETWEEN 1 AND 2147483647", name="ck_memories_capacity"),
        CheckConstraint("unit IN ('GB', 'TB')", name="ck_memories_unit"),
        CheckConstraint("code = capacity::text || unit", name="ck_memories_code"),
        Index("ix_memories_created_at_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    capacity: Mapped[int]
    unit: Mapped[str] = mapped_column(String(2))
    code: Mapped[str] = mapped_column(String(12))
    capacity_gb: Mapped[int] = mapped_column(
        BigInteger,
        Computed(
            "CASE WHEN unit = 'TB' THEN capacity::bigint * 1000 ELSE capacity::bigint END",
            persisted=True,
        ),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
