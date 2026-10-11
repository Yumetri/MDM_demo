from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from mdm_demo.presentation.dependencies import ModelLogService, RequestID
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses
from mdm_demo.presentation.schemas.model_examples import (
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    LOG_LIST_SUCCESS,
    LOG_SUCCESS,
    id_examples,
)
from mdm_demo.presentation.schemas.model_log import ModelLogResponse

router = APIRouter(tags=["ModelLog"])


@router.get(
    "/models/{model_id}/logs",
    summary="모델별 변경 이력 목록",
    description="삭제된 모델의 UUID도 조회할 수 있습니다. 기록 없는 UUID는 200 빈 목록입니다.",
    responses=responses(
        LOG_LIST_SUCCESS,
        dimension="model",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.model_id",
        page=True,
    ),
)
async def list_model_logs(
    model_id: Annotated[UUID, Path(openapi_examples=id_examples("model"))],
    service: ModelLogService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[ModelLogResponse]:
    page = await service.list(model_id, cursor, limit)
    return ListResponse(
        data=[ModelLogResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/model-logs/{log_id}",
    summary="변경 이력 단건 조회",
    description="이력 목록의 data[].id로 스냅샷을 조회합니다. 없는 로그는 404입니다.",
    responses=responses(
        LOG_SUCCESS,
        dimension="model",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.log_id",
    ),
)
async def get_model_log(
    log_id: Annotated[UUID, Path(openapi_examples=id_examples("log"))],
    service: ModelLogService,
    request_id: RequestID,
) -> SuccessResponse[ModelLogResponse]:
    log = await service.get(log_id)
    return SuccessResponse(
        data=ModelLogResponse.model_validate(log), meta=Meta(request_id=request_id)
    )
