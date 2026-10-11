from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.country import CountryService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.country import CountryResponse, CreateCountry, RenameCountry
from mdm_demo.presentation.schemas.country_examples import (
    COUNTRY_LIST_SUCCESS,
    COUNTRY_SUCCESS,
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    RENAME_EXAMPLES,
    id_examples,
)
from mdm_demo.presentation.schemas.examples import responses

CountryID = Annotated[UUID, Path(openapi_examples=id_examples("country"))]

router = APIRouter(prefix="/countries", tags=["Country"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="국가 생성",
    description="name과 code는 필수입니다. 이름은 대문자·NFC로 정규화합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        COUNTRY_SUCCESS,
        dimension="country",
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "COUNTRY_CODE_DUPLICATE",
            "COUNTRY_NAME_DUPLICATE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_country(
    body: Annotated[CreateCountry, Body(openapi_examples=CREATE_EXAMPLES)],
    service: CountryService,
    request_id: RequestID,
) -> SuccessResponse[CountryResponse]:
    country = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=CountryResponse.model_validate(country), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="국가 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        COUNTRY_LIST_SUCCESS,
        dimension="country",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_countries(
    service: CountryService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[CountryResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[CountryResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{country_id}",
    summary="국가 단건 조회",
    description="국가 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 국가는 404입니다.",
    responses=responses(
        COUNTRY_SUCCESS,
        dimension="country",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.country_id",
    ),
)
async def get_country(
    country_id: CountryID, service: CountryService, request_id: RequestID
) -> SuccessResponse[CountryResponse]:
    country = await service.get(country_id)
    return SuccessResponse(
        data=CountryResponse.model_validate(country), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{country_id}",
    summary="국가명 수정",
    description="국가명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        COUNTRY_SUCCESS,
        dimension="country",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "COUNTRY_NAME_DUPLICATE", "INTERNAL_ERROR"),
    ),
)
async def rename_country(
    country_id: CountryID,
    body: Annotated[RenameCountry, Body(openapi_examples=RENAME_EXAMPLES)],
    service: CountryService,
    request_id: RequestID,
) -> SuccessResponse[CountryResponse]:
    country = await service.rename(country_id, body.name, request_id)
    return SuccessResponse(
        data=CountryResponse.model_validate(country), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{country_id}",
    status_code=204,
    summary="국가 삭제 (이력 보존)",
    description="국가를 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.country_id",
        ),
    },
)
async def delete_country(
    country_id: Annotated[UUID, Path(openapi_examples=id_examples("country", success_status=204))],
    service: CountryService,
    request_id: RequestID,
) -> Response:
    await service.delete(country_id, request_id)
    return Response(status_code=204)
