from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateYear(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    year: int = Field(
        ge=1900,
        le=2999,
        description="제품 출시 연도. JSON 정수만 허용, 코드 자동 생성.",
    )


class ChangeYear(CreateYear):
    pass


class YearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    year: int
    code: str
    created_at: datetime
    updated_at: datetime
