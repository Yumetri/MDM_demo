from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path, Query, Response

from mdm_demo.presentation.dependencies import RequestID
from mdm_demo.presentation.dependencies.network import NetworkService
from mdm_demo.presentation.error_catalog import ERROR_RESPONSES
from mdm_demo.presentation.schemas.common import (
    ListMeta,
    ListResponse,
    Meta,
    PageMeta,
    SuccessResponse,
)
from mdm_demo.presentation.schemas.examples import responses
from mdm_demo.presentation.schemas.network import CreateNetwork, NetworkResponse, RenameNetwork
from mdm_demo.presentation.schemas.network_examples import (
    CREATE_EXAMPLES,
    CURSOR_DESCRIPTION,
    LIMIT_EXAMPLES,
    NETWORK_LIST_SUCCESS,
    NETWORK_SUCCESS,
    RENAME_EXAMPLES,
    id_examples,
)

NetworkID = Annotated[UUID, Path(openapi_examples=id_examples("network"))]

router = APIRouter(prefix="/networks", tags=["Network"], responses=ERROR_RESPONSES)


@router.post(
    "",
    status_code=201,
    summary="규격 생성",
    description="name은 필수이며 code 생략 시 이름의 ASCII 영문·숫자를 "
    "모두 추출합니다. 이름은 대문자·NFC로 정규화합니다. "
    "응답의 data.id를 후속 요청에 사용하세요.",
    responses=responses(
        NETWORK_SUCCESS,
        dimension="network",
        status=201,
        errors=(
            "VALIDATION_ERROR",
            "NETWORK_CODE_DUPLICATE",
            "NETWORK_NAME_DUPLICATE",
            "DIMENSION_AUTO_CODE_DUPLICATE",
            "DIMENSION_AUTO_CODE_UNAVAILABLE",
            "INTERNAL_ERROR",
        ),
    ),
)
async def create_network(
    body: Annotated[CreateNetwork, Body(openapi_examples=CREATE_EXAMPLES)],
    service: NetworkService,
    request_id: RequestID,
) -> SuccessResponse[NetworkResponse]:
    network = await service.create(body.name, body.code, request_id)
    return SuccessResponse(
        data=NetworkResponse.model_validate(network), meta=Meta(request_id=request_id)
    )


@router.get(
    "",
    summary="규격 목록",
    description="생성 시각·UUID 내림차순으로 조회합니다. 첫 페이지는 cursor를 생략하세요.",
    responses=responses(
        NETWORK_LIST_SUCCESS,
        dimension="network",
        errors=("INVALID_CURSOR", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="query.limit",
        page=True,
    ),
)
async def list_networks(
    service: NetworkService,
    request_id: RequestID,
    cursor: Annotated[str | None, Query(description=CURSOR_DESCRIPTION)] = None,
    limit: Annotated[int, Query(ge=1, le=100, openapi_examples=LIMIT_EXAMPLES)] = 20,
) -> ListResponse[NetworkResponse]:
    page = await service.list(cursor, limit)
    return ListResponse(
        data=[NetworkResponse.model_validate(item) for item in page.items],
        meta=ListMeta(
            request_id=request_id,
            page=PageMeta(next_cursor=page.next_cursor, has_next=page.has_next),
        ),
    )


@router.get(
    "/{network_id}",
    summary="규격 단건 조회",
    description="규격 UUID로 현재 데이터를 조회합니다. 없거나 삭제된 규격은 404입니다.",
    responses=responses(
        NETWORK_SUCCESS,
        dimension="network",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
        validation_field="path.network_id",
    ),
)
async def get_network(
    network_id: NetworkID, service: NetworkService, request_id: RequestID
) -> SuccessResponse[NetworkResponse]:
    network = await service.get(network_id)
    return SuccessResponse(
        data=NetworkResponse.model_validate(network), meta=Meta(request_id=request_id)
    )


@router.patch(
    "/{network_id}",
    summary="규격명 수정",
    description="규격명만 변경합니다. 동일한 이름이면 수정 시각과 이력이 유지됩니다.",
    responses=responses(
        NETWORK_SUCCESS,
        dimension="network",
        errors=("NOT_FOUND", "VALIDATION_ERROR", "NETWORK_NAME_DUPLICATE", "INTERNAL_ERROR"),
    ),
)
async def rename_network(
    network_id: NetworkID,
    body: Annotated[RenameNetwork, Body(openapi_examples=RENAME_EXAMPLES)],
    service: NetworkService,
    request_id: RequestID,
) -> SuccessResponse[NetworkResponse]:
    network = await service.rename(network_id, body.name, request_id)
    return SuccessResponse(
        data=NetworkResponse.model_validate(network), meta=Meta(request_id=request_id)
    )


@router.delete(
    "/{network_id}",
    status_code=204,
    summary="규격 삭제 (이력 보존)",
    description="규격을 물리 삭제하고 이력은 보존합니다. "
    "같은 코드로 재생성하면 새 UUID를 받습니다.",
    responses={
        204: {"description": "삭제 완료. 응답 본문 없음. 재삭제는 404 NOT_FOUND."},
        **responses(
            errors=("NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"),
            validation_field="path.network_id",
        ),
    },
)
async def delete_network(
    network_id: Annotated[UUID, Path(openapi_examples=id_examples("network", success_status=204))],
    service: NetworkService,
    request_id: RequestID,
) -> Response:
    await service.delete(network_id, request_id)
    return Response(status_code=204)
