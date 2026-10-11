from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mdm_demo.infrastructure.persistence.models.base import Base


class ModelLogModel(Base):
    __tablename__ = "model_logs"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="ck_model_logs_operation"
        ),
        CheckConstraint(
            "(operation = 'create' AND before IS NULL AND after IS NOT NULL) OR "
            "(operation = 'update' AND before IS NOT NULL AND after IS NOT NULL) OR "
            "(operation = 'delete' AND before IS NOT NULL AND after IS NULL)",
            name="ck_model_logs_snapshots",
        ),
        Index("ix_model_logs_model_time", "model_id", "occurred_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    model_id: Mapped[UUID]
    operation: Mapped[str] = mapped_column(String(10))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[UUID]
    before: Mapped[dict[str, str] | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[dict[str, str] | None] = mapped_column(JSONB(none_as_null=True))
