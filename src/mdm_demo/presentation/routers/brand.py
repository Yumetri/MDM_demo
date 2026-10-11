from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.brand import BrandService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.brand import BrandResponse, CreateBrand, RenameBrand
from mdm_demo.presentation.schemas.brand_examples import (
    BRAND_LIST_SUCCESS,
    BRAND_SUCCESS,
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

BrandID = Annotated[UUID, Path(openapi_examples=id_examples("brand"))]

router = APIRouter(prefix="/brands", tags=["Brand"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="브랜드 생성",
    description="code를 생략하면 브랜드명에서 자동 생성합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        BRAND_SUCCESS,
        dimension="brand",
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "BRAND_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_UNAVAILABLE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_brand(
    body: Annotated[CreateBrand, Body(openapi_examples=CREATE_EXAMPLES)],
    service: BrandService,
    request_id: RequestID,
) -> SuccessResponse[BrandResponse]:
    brand = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=BrandResponse.model_validate(brand), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="브랜드 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        BRAND_LIST_SUCCESS,
        dimension="brand",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_brands(
    service: BrandService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[BrandResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[BrandResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{brand_id}",
    summary="브랜드 단건 조회",
    description="브랜드 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 브랜드는 404입니다.",
    responses=responses(
        BRAND_SUCCESS,
        dimension="brand",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.brand_id",
    ),
)
async def get_brand(
    brand_id: BrandID, service: BrandService, request_id: RequestID
) -> SuccessResponse[BrandResponse]:
    brand = await service.get(brand_id)
    return SuccessResponse(
        data=BrandResponse.model_validate(brand), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{brand_id}",
    summary="브랜드명 수정",
    description="브랜드명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        BRAND_SUCCESS, dimension="brand", errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR")
    ),
)
async def rename_brand(
    brand_id: BrandID,
    body: Annotated[RenameBrand, Body(openapi_examples=RENAME_EXAMPLES)],
    service: BrandService,
    request_id: RequestID,
) -> SuccessResponse[BrandResponse]:
    brand = await service.rename(brand_id, body.name, request_id)
    return SuccessResponse(
        data=BrandResponse.model_validate(brand), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{brand_id}",
    status_code=204,
    summary="브랜드 삭제 (이력 보존)",
    description="브랜드를 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.brand_id",
        ),
    },
)
async def delete_brand(
    brand_id: Annotated[UUID, Path(openapi_examples=id_examples("brand", success_status=204))],
    service: BrandService,
    request_id: RequestID,
) -> Response:
    await service.delete(brand_id, request_id)
    return Response(status_code=204)
