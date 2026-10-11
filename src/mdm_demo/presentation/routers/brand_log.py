from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from mdm_demo.presentation.dependencies import BrandLogService, RequestID
from mdm_demo.presentation.schemas.brand_examples import (
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    LOG_LIST_SUCCESS,
    LOG_SUCCESS,
    id_examples,
)
from mdm_demo.presentation.schemas.brand_log import BrandLogResponse
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses

router = APIRouter(tags=["BrandLog"])


@router.get(
    "/brands/{brand_id}/logs",
    summary="브랜드별 변경 이력 목록",
    description="삭제된 브랜드의 UUID도 조회할 수 있습니다. 기록 없는 UUID는 200 빈 목록입니다.",
    responses=responses(
        LOG_LIST_SUCCESS,
        dimension="brand",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.brand_id",
        page=True,
    ),
)
async def list_brand_logs(
    brand_id: Annotated[UUID, Path(openapi_examples=id_examples("brand"))],
    service: BrandLogService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[BrandLogResponse]:
    page = await service.list(brand_id, cursor, limit)
    return ListResponse(
        data=[BrandLogResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/brand-logs/{log_id}",
    summary="변경 이력 단건 조회",
    description="이력 목록의 data[].id로 스냅샷을 조회합니다. 없는 로그는 404입니다.",
    responses=responses(
        LOG_SUCCESS,
        dimension="brand",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.log_id",
    ),
)
async def get_brand_log(
    log_id: Annotated[UUID, Path(openapi_examples=id_examples("log"))],
    service: BrandLogService,
    request_id: RequestID,
) -> SuccessResponse[BrandLogResponse]:
    log = await service.get(log_id)
    return SuccessResponse(
        data=BrandLogResponse.model_validate(log), meta=Meta(request_id=request_id)
    )
