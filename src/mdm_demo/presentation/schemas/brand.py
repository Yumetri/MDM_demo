from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateBrand(BaseModel):
    name: str = Field(
        description="양끝 공백 제거 후 1~100자. 내부 공백 유지. NUL·단독 surrogate 불허."
    )
    code: Annotated[
        str | None,
        Field(
            description="양끝 공백 제거 후 ASCII 영문·숫자 3자. "
            "생략만 자동 생성이며 null은 허용하지 않음.",
        ),
    ] = None

    @field_validator("code", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Code cannot be null")
        return value

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "properties": {
                "name": {
                    "type": "string",
                    "description": "양끝 공백 제거 후 1~100자. NUL·단독 surrogate 불허.",
                },
                "code": {
                    "type": "string",
                    "description": "생략 시 자동 생성. 양끝 공백 제거. "
                    "null·빈 값·내부 공백은 허용하지 않음.",
                },
            }
        },
    )


class RenameBrand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(description="양끝 공백 제거 후 1~100자. NUL·단독 surrogate 불허.")


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime
