from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import ModelService, RequestID
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses
from mdm_demo.presentation.schemas.model import CreateModel, ModelResponse, RenameModel
from mdm_demo.presentation.schemas.model_examples import (
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    MODEL_LIST_SUCCESS,
    MODEL_SUCCESS,
    RENAME_EXAMPLES,
    id_examples,
)

ModelID = Annotated[UUID, Path(openapi_examples=id_examples("model"))]

router = APIRouter(prefix="/models", tags=["Model"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="모델 생성",
    description="code를 생략하면 모델명에서 자동 생성합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        MODEL_SUCCESS,
        dimension="model",
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "MODEL_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_UNAVAILABLE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_model(
    body: Annotated[CreateModel, Body(openapi_examples=CREATE_EXAMPLES)],
    service: ModelService,
    request_id: RequestID,
) -> SuccessResponse[ModelResponse]:
    model = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=ModelResponse.model_validate(model), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="모델 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        MODEL_LIST_SUCCESS,
        dimension="model",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_models(
    service: ModelService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[ModelResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[ModelResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{model_id}",
    summary="모델 단건 조회",
    description="모델 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 모델은 404입니다.",
    responses=responses(
        MODEL_SUCCESS,
        dimension="model",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.model_id",
    ),
)
async def get_model(
    model_id: ModelID, service: ModelService, request_id: RequestID
) -> SuccessResponse[ModelResponse]:
    model = await service.get(model_id)
    return SuccessResponse(
        data=ModelResponse.model_validate(model), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{model_id}",
    summary="모델명 수정",
    description="모델명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        MODEL_SUCCESS, dimension="model", errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR")
    ),
)
async def rename_model(
    model_id: ModelID,
    body: Annotated[RenameModel, Body(openapi_examples=RENAME_EXAMPLES)],
    service: ModelService,
    request_id: RequestID,
) -> SuccessResponse[ModelResponse]:
    model = await service.rename(model_id, body.name, request_id)
    return SuccessResponse(
        data=ModelResponse.model_validate(model), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{model_id}",
    status_code=204,
    summary="모델 삭제 (이력 보존)",
    description="모델을 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.model_id",
        ),
    },
)
async def delete_model(model_id: ModelID, service: ModelService, request_id: RequestID) -> Response:
    await service.delete(model_id, request_id)
    return Response(status_code=204)
