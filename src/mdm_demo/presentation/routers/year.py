from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.year import YearService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses
from mdm_demo.presentation.schemas.year import ChangeYear, CreateYear, YearResponse
from mdm_demo.presentation.schemas.year_examples import (
    CHANGE_EXAMPLES,
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    YEAR_LIST_SUCCESS,
    YEAR_SUCCESS,
    id_examples,
)

YearID = Annotated[UUID, Path(openapi_examples=id_examples("year"))]

router = APIRouter(prefix="/years", tags=["Year"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="출시 연도 생성",
    description="year 정수만 입력하세요. 코드는 해당 연도로 자동 생성합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        YEAR_SUCCESS,
        dimension="year",
        status=201,
        validation_field="body.year",
        errors=(
            "VALIDATION_ERROR",
            "YEAR_DUPLICATE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_year(
    body: Annotated[CreateYear, Body(openapi_examples=CREATE_EXAMPLES)],
    service: YearService,
    request_id: RequestID,
) -> SuccessResponse[YearResponse]:
    year = await service.create(body.year, request_id)
    return SuccessResponse(data=YearResponse.model_validate(year), meta=Meta(request_id=request_id))


@router.get(
    "",
    summary="출시 연도 목록",
    description="연도 내림차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        YEAR_LIST_SUCCESS,
        dimension="year",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_years(
    service: YearService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[YearResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[YearResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{year_id}",
    summary="출시 연도 단건 조회",
    description=("출시 연도 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 출시 연도는 404입니다."),
    responses=responses(
        YEAR_SUCCESS,
        dimension="year",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.year_id",
    ),
)
async def get_year(
    year_id: YearID, service: YearService, request_id: RequestID
) -> SuccessResponse[YearResponse]:
    year = await service.get(year_id)
    return SuccessResponse(data=YearResponse.model_validate(year), meta=Meta(request_id=request_id))


@router.patch(
    "/{year_id}",
    summary="출시 연도 수정",
    description=(
        "연도와 자동 코드를 함께 변경합니다. 같은 연도면 수정 "
        "시각·이력이 유지됩니다. 중복은 409입니다."
    ),
    responses=responses(
        YEAR_SUCCESS,
        dimension="year",
        errors=("NOT_FOUND", "YEAR_DUPLICATE", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="body.year",
    ),
)
async def change_year(
    year_id: YearID,
    body: Annotated[ChangeYear, Body(openapi_examples=CHANGE_EXAMPLES)],
    service: YearService,
    request_id: RequestID,
) -> SuccessResponse[YearResponse]:
    year = await service.change_year(year_id, body.year, request_id)
    return SuccessResponse(data=YearResponse.model_validate(year), meta=Meta(request_id=request_id))


@router.delete(
    "/{year_id}",
    status_code=204,
    summary="출시 연도 삭제 (이력 보존)",
    description="출시 연도를 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.year_id",
        ),
    },
)
async def delete_year(
    year_id: Annotated[UUID, Path(openapi_examples=id_examples("year", success_status=204))],
    service: YearService,
    request_id: RequestID,
) -> Response:
    await service.delete(year_id, request_id)
    return Response(status_code=204)
