from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.memory import MemoryLogService
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.memory_examples import (
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    LOG_LIST_SUCCESS,
    LOG_SUCCESS,
    id_examples,
    responses,
)
from mdm_demo.presentation.schemas.memory_log import MemoryLogResponse

router = APIRouter(tags=["MemoryLog"])


@router.get(
    "/memories/{memory_id}/logs",
    summary="Memory별 변경 이력 목록",
    description="삭제된 Memory의 UUID도 조회할 수 있습니다. 기록 없는 UUID는 200 빈 목록입니다.",
    responses=responses(
        LOG_LIST_SUCCESS,
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.memory_id",
        page=True,
    ),
)
async def list_memory_logs(
    memory_id: Annotated[UUID, Path(openapi_examples=id_examples("memory", log_list=True))],
    service: MemoryLogService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[MemoryLogResponse]:
    page = await service.list(memory_id, cursor, limit)
    return ListResponse(
        data=[MemoryLogResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/memory-logs/{log_id}",
    summary="변경 이력 단건 조회",
    description="이력 목록의 data[].id로 스냅샷을 조회합니다. 없는 로그는 404입니다.",
    responses=responses(
        LOG_SUCCESS,
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.log_id",
    ),
)
async def get_memory_log(
    log_id: Annotated[UUID, Path(openapi_examples=id_examples("log"))],
    service: MemoryLogService,
    request_id: RequestID,
) -> SuccessResponse[MemoryLogResponse]:
    log = await service.get(log_id)
    return SuccessResponse(
        data=MemoryLogResponse.model_validate(log), meta=Meta(request_id=request_id)
    )
