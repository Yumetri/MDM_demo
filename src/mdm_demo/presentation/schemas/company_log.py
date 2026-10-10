from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanySnapshot(BaseModel):
    id: UUID
    name: str
    code: str


class CompanyLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    operation: Literal["create", "update", "delete"]
    occurred_at: datetime
    request_id: UUID = Field(
        description="변경 당시 요청 ID. 현재 조회 요청의 meta.request_id와 다름."
    )
    before: CompanySnapshot | None
    after: CompanySnapshot | None
