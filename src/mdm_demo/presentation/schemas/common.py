from uuid import UUID

from pydantic import BaseModel


class PageMeta(BaseModel):
    next_cursor: str | None
    has_next: bool


class Meta(BaseModel):
    request_id: UUID


class ListMeta(Meta):
    page: PageMeta


class SuccessResponse[T](BaseModel):
    data: T
    meta: Meta


class ListResponse[T](BaseModel):
    data: list[T]
    meta: ListMeta


class ErrorDetail(BaseModel):
    field: str | None
    code: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    error: ErrorBody
    meta: Meta
