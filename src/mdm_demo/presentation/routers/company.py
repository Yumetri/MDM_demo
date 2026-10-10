from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import CompanyService, RequestID
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.company import CompanyResponse, CreateCompany, RenameCompany
from mdm_demo.presentation.schemas.examples import (
    COMPANY_LIST_SUCCESS,
    COMPANY_SUCCESS,
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    RENAME_EXAMPLES,
    id_examples,
    responses,
)

CompanyID = Annotated[UUID, Path(openapi_examples=id_examples("company"))]

router = APIRouter(prefix="/companies", tags=["Company"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="회사 생성",
    description="code를 생략하면 회사명에서 자동 생성합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        COMPANY_SUCCESS,
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "COMPANY_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_UNAVAILABLE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_company(
    body: Annotated[CreateCompany, Body(openapi_examples=CREATE_EXAMPLES)],
    service: CompanyService,
    request_id: RequestID,
) -> SuccessResponse[CompanyResponse]:
    company = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=CompanyResponse.model_validate(company), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="회사 목록",
    description="생성 시각·UUID 오름차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        COMPANY_LIST_SUCCESS,
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_companies(
    service: CompanyService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[CompanyResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[CompanyResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{company_id}",
    summary="회사 단건 조회",
    description="회사 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 회사는 404입니다.",
    responses=responses(
        COMPANY_SUCCESS,
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.company_id",
    ),
)
async def get_company(
    company_id: CompanyID, service: CompanyService, request_id: RequestID
) -> SuccessResponse[CompanyResponse]:
    company = await service.get(company_id)
    return SuccessResponse(
        data=CompanyResponse.model_validate(company), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{company_id}",
    summary="회사명 수정",
    description="회사명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        COMPANY_SUCCESS, errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR")
    ),
)
async def rename_company(
    company_id: CompanyID,
    body: Annotated[RenameCompany, Body(openapi_examples=RENAME_EXAMPLES)],
    service: CompanyService,
    request_id: RequestID,
) -> SuccessResponse[CompanyResponse]:
    company = await service.rename(company_id, body.name, request_id)
    return SuccessResponse(
        data=CompanyResponse.model_validate(company), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{company_id}",
    status_code=204,
    summary="회사 삭제 (이력 보존)",
    description="회사를 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.company_id",
        ),
    },
)
async def delete_company(
    company_id: CompanyID, service: CompanyService, request_id: RequestID
) -> Response:
    await service.delete(company_id, request_id)
    return Response(status_code=204)
