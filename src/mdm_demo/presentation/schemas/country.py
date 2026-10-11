from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateCountry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(description="양끝 공백 제거·대문자·NFC 정규화 후 1~100자. 중복 불가.")
    code: str = Field(
        description="필수. 양끝 공백 제거 후 ASCII 영문 3자, 대문자 저장. 자동 생성 없음."
    )


class RenameCountry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(description="양끝 공백 제거·대문자·NFC 정규화 후 1~100자. 중복 불가.")


class CountryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime
