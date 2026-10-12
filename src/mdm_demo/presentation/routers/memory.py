from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.memory import MemoryService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.memory import ChangeMemorySize, CreateMemory, MemoryResponse
from mdm_demo.presentation.schemas.memory_examples import (
    CHANGE_EXAMPLES,
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    MEMORY_LIST_SUCCESS,
    MEMORY_SUCCESS,
    id_examples,
    responses,
)

MemoryID = Annotated[UUID, Path(openapi_examples=id_examples("memory"))]

router = APIRouter(prefix="/memories", tags=["Memory"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="저장공간 용량 생성",
    description="capacity와 unit을 입력하면 코드가 자동 생성됩니다. 1TB와 1000GB는 중복입니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        MEMORY_SUCCESS,
        status=201,
        validation_field="body.capacity",
        errors=(
            "VALIDATION_ERROR",
            "MEMORY_CAPACITY_DUPLICATE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_memory(
    body: Annotated[CreateMemory, Body(openapi_examples=CREATE_EXAMPLES)],
    service: MemoryService,
    request_id: RequestID,
) -> SuccessResponse[MemoryResponse]:
    memory = await service.create(body.capacity, body.unit, request_id)
    return SuccessResponse(
        data=MemoryResponse.model_validate(memory), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="저장공간 용량 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        MEMORY_LIST_SUCCESS,
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_memories(
    service: MemoryService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[MemoryResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[MemoryResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{memory_id}",
    summary="저장공간 용량 단건 조회",
    description="Memory UUID로 현재 데이터를 조회합니다. 없거나 삭제된 Memory는 404입니다.",
    responses=responses(
        MEMORY_SUCCESS,
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.memory_id",
    ),
)
async def get_memory(
    memory_id: MemoryID, service: MemoryService, request_id: RequestID
) -> SuccessResponse[MemoryResponse]:
    memory = await service.get(memory_id)
    return SuccessResponse(
        data=MemoryResponse.model_validate(memory), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{memory_id}",
    summary="저장공간 용량 수정",
    description="capacity와 unit 모두 필수이며 코드도 자동 갱신됩니다. 같은 표기면 시각·이력 유지, "
    "1TB→1000GB는 표기 변경 이력을 남깁니다.",
    responses=responses(
        MEMORY_SUCCESS,
        errors=("NOT_FOUND", "VALIDATION_ERROR", "MEMORY_CAPACITY_DUPLICATE", "INTERNAL_ERROR"),
        validation_field="body.capacity",
    ),
)
async def change_memory_size(
    memory_id: MemoryID,
    body: Annotated[ChangeMemorySize, Body(openapi_examples=CHANGE_EXAMPLES)],
    service: MemoryService,
    request_id: RequestID,
) -> SuccessResponse[MemoryResponse]:
    memory = await service.change_size(memory_id, body.capacity, body.unit, request_id)
    return SuccessResponse(
        data=MemoryResponse.model_validate(memory), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{memory_id}",
    status_code=204,
    summary="저장공간 용량 삭제 (이력 보존)",
    description="Memory를 물리 삭제하고 이력은 보존합니다. "
    "같은 용량으로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.memory_id",
        ),
    },
)
async def delete_memory(
    memory_id: Annotated[UUID, Path(openapi_examples=id_examples("memory", success_status=204))],
    service: MemoryService,
    request_id: RequestID,
) -> Response:
    await service.delete(memory_id, request_id)
    return Response(status_code=204)
