from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemorySnapshot(BaseModel):
    id: UUID
    capacity: int
    unit: Literal["GB", "TB"]
    code: str


class MemoryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    memory_id: UUID
    operation: Literal["create", "update", "delete"]
    occurred_at: datetime
    request_id: UUID = Field(
        description="변경 당시 요청 ID. 현재 조회 요청 meta.request_id와 다름."
    )
    before: MemorySnapshot | None
    after: MemorySnapshot | None
