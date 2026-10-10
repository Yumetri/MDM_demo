from dataclasses import dataclass
from typing import Any

from mdm_demo.presentation.schemas.common import ErrorResponse


@dataclass(frozen=True)
class ErrorSpec:
    status: int
    message: str


ERRORS = {
    "VALIDATION_ERROR": ErrorSpec(422, "요청 값이 올바르지 않습니다."),
    "INVALID_CURSOR": ErrorSpec(400, "페이지 커서가 올바르지 않습니다."),
    "BAD_REQUEST": ErrorSpec(400, "요청을 처리할 수 없습니다."),
    "UNAUTHENTICATED": ErrorSpec(401, "인증이 필요합니다."),
    "FORBIDDEN": ErrorSpec(403, "이 작업을 수행할 권한이 없습니다."),
    "NOT_FOUND": ErrorSpec(404, "요청한 대상을 찾을 수 없습니다."),
    "METHOD_NOT_ALLOWED": ErrorSpec(405, "지원하지 않는 요청 방식입니다."),
    "CONFLICT": ErrorSpec(409, "현재 상태에서는 요청을 처리할 수 없습니다."),
    "INTERNAL_ERROR": ErrorSpec(500, "요청 처리 중 오류가 발생했습니다."),
    "COMPANY_CODE_DUPLICATE": ErrorSpec(409, "이미 존재하는 회사 코드입니다."),
    "DIMENSION_AUTO_CODE_DUPLICATE": ErrorSpec(
        409, "자동 생성된 코드가 이미 존재합니다. 코드를 직접 입력해 주세요."
    ),
    "DIMENSION_AUTO_CODE_UNAVAILABLE": ErrorSpec(
        422, "company에서 코드를 자동으로 생성할 수 없습니다. 코드를 직접 입력해 주세요."
    ),
}

DETAIL_MESSAGES = {
    "INVALID_VALUE": "입력 값의 형식과 허용 범위를 확인해 주세요.",
    "OUT_OF_RANGE": "1 이상 100 이하의 값을 입력해 주세요.",
}

HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (400, 404, 405, 409, 422, 500)
}
