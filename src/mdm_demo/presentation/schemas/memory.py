from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateMemory(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    capacity: int = Field(
        ge=1, le=2_147_483_647, description="JSON 정수만 허용. 문자열·실수·불리언은 거부합니다."
    )
    unit: str = Field(description="양끝 공백 제거·대문자 변환 후 GB 또는 TB. 1TB=1000GB.")


class ChangeMemorySize(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    capacity: int = Field(
        ge=1, le=2_147_483_647, description="필수 JSON 정수. 코드도 자동 갱신됩니다."
    )
    unit: str = Field(description="필수. 양끝 공백 제거·대문자 변환 후 GB 또는 TB.")


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    capacity: int
    unit: Literal["GB", "TB"]
    code: str
    created_at: datetime
    updated_at: datetime
