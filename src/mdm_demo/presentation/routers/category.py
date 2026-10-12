from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.category import CategoryService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.category import CategoryResponse, CreateCategory, RenameCategory
from mdm_demo.presentation.schemas.category_examples import (
    CATEGORY_LIST_SUCCESS,
    CATEGORY_SUCCESS,
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    RENAME_EXAMPLES,
    id_examples,
)
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses

CategoryID = Annotated[UUID, Path(openapi_examples=id_examples("category"))]

router = APIRouter(prefix="/categories", tags=["Category"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="분류 생성",
    description="name은 필수이며 code 생략 시 이름에서 영문·숫자 앞 3자로 "
    "자동 생성합니다. 이름은 대문자·NFC로 정규화합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        CATEGORY_SUCCESS,
        dimension="category",
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "CATEGORY_CODE_DUPLICATE",
            "CATEGORY_NAME_DUPLICATE",
            "DIMENSION_AUTO_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_UNAVAILABLE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_category(
    body: Annotated[CreateCategory, Body(openapi_examples=CREATE_EXAMPLES)],
    service: CategoryService,
    request_id: RequestID,
) -> SuccessResponse[CategoryResponse]:
    category = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=CategoryResponse.model_validate(category), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="분류 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        CATEGORY_LIST_SUCCESS,
        dimension="category",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_categories(
    service: CategoryService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[CategoryResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[CategoryResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{category_id}",
    summary="분류 단건 조회",
    description="분류 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 분류는 404입니다.",
    responses=responses(
        CATEGORY_SUCCESS,
        dimension="category",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.category_id",
    ),
)
async def get_category(
    category_id: CategoryID, service: CategoryService, request_id: RequestID
) -> SuccessResponse[CategoryResponse]:
    category = await service.get(category_id)
    return SuccessResponse(
        data=CategoryResponse.model_validate(category), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{category_id}",
    summary="분류명 수정",
    description="분류명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        CATEGORY_SUCCESS,
        dimension="category",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "CATEGORY_NAME_DUPLICATE", "INTERNAL_ERROR"),
    ),
)
async def rename_category(
    category_id: CategoryID,
    body: Annotated[RenameCategory, Body(openapi_examples=RENAME_EXAMPLES)],
    service: CategoryService,
    request_id: RequestID,
) -> SuccessResponse[CategoryResponse]:
    category = await service.rename(category_id, body.name, request_id)
    return SuccessResponse(
        data=CategoryResponse.model_validate(category), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="분류 삭제 (이력 보존)",
    description="분류를 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.category_id",
        ),
    },
)
async def delete_category(
    category_id: Annotated[
        UUID, Path(openapi_examples=id_examples("category", success_status=204))
    ],
    service: CategoryService,
    request_id: RequestID,
) -> Response:
    await service.delete(category_id, request_id)
    return Response(status_code=204)
