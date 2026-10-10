"""Executable OpenAPI examples; messages come from the shared error catalog."""

from typing import Any

from mdm_demo.presentation.error_catalog import DETAIL_MESSAGES, ERRORS
from mdm_demo.presentation.schemas.common import ErrorResponse

COMPANY_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
COMPANY = {
    "id": COMPANY_ID,
    "name": "Samsung",
    "code": "SAM",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: COMPANY[key] for key in ("id", "name", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "name": "Samsung Electronics"}
LOG = {
    "id": LOG_ID,
    "company_id": COMPANY_ID,
    "operation": "create",
    "occurred_at": "2026-10-10T00:00:00Z",
    "request_id": CHANGE_REQUEST_ID,
    "before": None,
    "after": SNAPSHOT,
}


def example(summary: str, value: Any, description: str = "", **extensions: Any) -> dict[str, Any]:
    return {"summary": summary, "description": description, "value": value, **extensions}


def request_example(summary: str, value: Any, status: int, description: str = "") -> dict[str, Any]:
    return example(summary, value, description, **{"x-expected-status": status})


CREATE_EXAMPLES = {
    "auto_code": request_example(
        "201 · 코드 생략 → SAM",
        {"name": "Samsung"},
        201,
        "SAM 코드가 없을 때 성공. 재실행하면 DIMENSION_AUTO_CODE_DUPLICATE/409. "
        "정리는 응답 data.id로 DELETE /companies/{company_id}.",
    ),
    "manual_code": request_example(
        "201 · 한글 이름 + 소문자 코드 → ABC",
        {"name": "삼성전자", "code": "abc"},
        201,
        "ABC 코드가 없어야 합니다. 이름은 중복 허용, 코드는 중복 불가.",
    ),
    "trim_name": request_example(
        "201 · 이름 양끝만 공백 제거",
        {"name": "  Example  Company  ", "code": "TST"},
        201,
        "TST가 없어야 합니다. 내부 두 칸 공백은 보존합니다.",
    ),
    "name_boundary": request_example(
        "201 · 이름 길이 상한 200자",
        {"name": "가" * 200, "code": "MAX"},
        201,
        "MAX 코드가 없어야 합니다.",
    ),
    "duplicate_manual": request_example(
        "409 · 직접 입력 코드 중복",
        {"name": "Another", "code": "sam"},
        409,
        "먼저 auto_code 예제를 실행해 SAM을 생성합니다. COMPANY_CODE_DUPLICATE.",
    ),
    "duplicate_auto": request_example(
        "409 · 자동 생성 코드 중복",
        {"name": "Samson"},
        409,
        "먼저 auto_code 예제로 SAM을 생성합니다. DIMENSION_AUTO_CODE_DUPLICATE.",
    ),
    "auto_unavailable": request_example(
        "422 · 영문 부족 → 자동 생성 불가",
        {"name": "LG"},
        422,
        "DIMENSION_AUTO_CODE_UNAVAILABLE. 코드를 직접 입력하면 생성 가능.",
    ),
    "null_code": request_example(
        "422 · null은 생략이 아님",
        {"name": "Samsung", "code": None},
        422,
        "VALIDATION_ERROR. 자동 생성은 code 필드 자체를 생략해야 합니다.",
    ),
    "empty_code": request_example(
        "422 · 빈 코드는 자동 생성 아님", {"name": "Samsung", "code": ""}, 422, "VALIDATION_ERROR."
    ),
    "space_code": request_example(
        "422 · 코드 공백은 제거하지 않음",
        {"name": "Samsung", "code": " ABC"},
        422,
        "VALIDATION_ERROR.",
    ),
    "non_ascii_code": request_example(
        "422 · 전각 영문 코드 불가",
        {"name": "Samsung", "code": "ＡＢＣ"},
        422,
        "VALIDATION_ERROR. ASCII 영문 3자만 허용.",
    ),
    "blank_name": request_example(
        "422 · 공백만 있는 이름", {"name": "   ", "code": "ABC"}, 422, "VALIDATION_ERROR."
    ),
    "long_name": request_example(
        "422 · 이름 201자", {"name": "가" * 201, "code": "ABC"}, 422, "VALIDATION_ERROR."
    ),
    "extra_field": request_example(
        "422 · 알 수 없는 필드",
        {"name": "Samsung", "code": "ABC", "memo": "허용되지 않는 필드"},
        422,
        "VALIDATION_ERROR.",
    ),
    "wrong_type": request_example(
        "422 · 이름은 문자열", {"name": 123, "code": "ABC"}, 422, "VALIDATION_ERROR."
    ),
}
RENAME_EXAMPLES = {
    "rename": request_example(
        "200 · 이름 변경",
        {"name": "Samsung Electronics"},
        200,
        "먼저 POST로 생성하고 반환된 data.id를 경로에 넣습니다. 코드는 유지됩니다.",
    ),
    "no_change": request_example(
        "200 · 동일 이름 → 시각·이력 유지",
        {"name": " Samsung "},
        200,
        "현재 이름이 Samsung인 회사에서 실행합니다. 다르면 일반 이름 변경입니다.",
    ),
    "unicode": request_example("200 · 한글·이모지 이름", {"name": "삼성전자🙂"}, 200),
    "immutable_code": request_example(
        "422 · 코드는 수정 불가", {"name": "New", "code": "NEW"}, 422, "VALIDATION_ERROR."
    ),
    "empty_body": request_example(
        "422 · 빈 수정 요청", {}, 422, "VALIDATION_ERROR. name이 필수입니다."
    ),
    "null_name": request_example("422 · null 이름", {"name": None}, 422, "VALIDATION_ERROR."),
    "blank_name": request_example(
        "422 · 공백만 있는 이름", {"name": "  "}, 422, "VALIDATION_ERROR."
    ),
    "long_name": request_example(
        "422 · 이름 201자", {"name": "가" * 201}, 422, "VALIDATION_ERROR."
    ),
}


def id_examples(kind: str) -> dict[str, Any]:
    return {
        "replace_with_actual_id": example(
            "실제 응답 UUID로 교체",
            LOG_ID if kind == "log" else COMPANY_ID,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "회사별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /companies의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            ),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은200 빈 배열, "
            "회사·로그 단건/수정/삭제는404 NOT_FOUND.",
        ),
        "invalid": example("422 · UUID 형식 오류", "not-a-uuid", "VALIDATION_ERROR."),
    }


LIMIT_EXAMPLES = {
    "small_page": example(
        "200 · 페이지 순회 확인", 1, "항목이2개 이상이면 다음 cursor가 반환됩니다."
    ),
    "default_page": example("200 · 기본 크기", 20),
    "max_page": example("200 · 최대 크기", 100),
    "zero": example("422 · 하한 미만", 0, "VALIDATION_ERROR / OUT_OF_RANGE."),
    "too_large": example("422 · 상한 초과", 101, "VALIDATION_ERROR / OUT_OF_RANGE."),
    "wrong_type": example("422 · 정수 아님", "many", "VALIDATION_ERROR / INVALID_VALUE."),
}
CURSOR_DESCRIPTION = (
    "첫 페이지는 cursor를 보내지 마세요(빈 문자열도400). 다음 페이지는 같은 목록 응답의 "
    "meta.page.next_cursor를 그대로 복사하세요. "
    "서명·경계값은 서버가 생성하며 고정 정상 예제는 없습니다. "
    "다른 목록/다른 회사의 cursor는400 INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor 또는 cursor=를 추가하세요(400 INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


def error_example(
    code: str, field: str | None = None, *, detail_code: str | None = None
) -> dict[str, Any]:
    spec = ERRORS[code]
    details = []
    if field:
        selected = detail_code or code
        message = DETAIL_MESSAGES[selected] if detail_code else spec.message
        details = [{"field": field, "code": selected, "message": message}]
    return example(
        f"{spec.status} · {code}",
        {
            "error": {"code": code, "message": spec.message, "details": details},
            "meta": META,
        },
    )


def responses(
    success: dict[str, Any] | None = None,
    *,
    status: int = 200,
    errors: tuple[str, ...] = (),
    validation_field: str = "body.name",
    page: bool = False,
) -> dict[int | str, dict[str, Any]]:
    result: dict[int | str, dict[str, Any]] = {}
    if success is not None:
        result[status] = {"content": {"application/json": {"examples": success}}}
    for code in errors:
        spec = ERRORS[code]
        response = result.setdefault(
            spec.status, {"model": ErrorResponse, "content": {"application/json": {"examples": {}}}}
        )
        field = (
            "body.code"
            if code
            in {
                "COMPANY_CODE_DUPLICATE",
                "DIMENSION_AUTO_CODE_DUPLICATE",
                "DIMENSION_AUTO_CODE_UNAVAILABLE",
            }
            else None
        )
        response["content"]["application/json"]["examples"][code] = error_example(code, field)
    if "VALIDATION_ERROR" in errors:
        examples = result[422]["content"]["application/json"]["examples"]
        examples["VALIDATION_ERROR"] = error_example(
            "VALIDATION_ERROR", validation_field, detail_code="INVALID_VALUE"
        )
        if page:
            examples["limit_range"] = error_example(
                "VALIDATION_ERROR", "query.limit", detail_code="OUT_OF_RANGE"
            )
    return result


COMPANY_SUCCESS = {
    "company": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": COMPANY, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
COMPANY_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [COMPANY], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
    ),
    "empty": example("200 · 빈 목록", EMPTY_PAGE),
}
LOG_SUCCESS = {
    "created": example("생성 이력 · before=null", {"data": LOG, "meta": META}),
    "updated": example(
        "수정 이력 · 이전/이후 값",
        {
            "data": {**LOG, "operation": "update", "before": SNAPSHOT, "after": UPDATED_SNAPSHOT},
            "meta": META,
        },
    ),
    "deleted": example(
        "삭제 이력 · after=null",
        {
            "data": {**LOG, "operation": "delete", "before": UPDATED_SNAPSHOT, "after": None},
            "meta": META,
        },
    ),
}
LOG_LIST_SUCCESS = {
    "last_page": example(
        "200 · 생성 이력 마지막 페이지",
        {"data": [LOG], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
    ),
    "empty": example("200 · 기록 없는 회사 UUID", EMPTY_PAGE),
}
WORKFLOW = """### HTTP 테스트 순서
1. POST /companies의 `auto_code` 예제로 생성하고 `data.id`를 복사합니다.
   이미 SAM이 있다면 직접 입력 코드로 새 회사를 생성하거나 본인이 만든 테스트 회사를 정리합니다.
2. 그 UUID로 단건 조회·이름 수정·회사별 이력 목록을 실행합니다.
   `no_change` 예제는 현재 이름이 Samsung일 때만 이력이 늘지 않습니다.
3. 이력 목록의 `data[].id`를 `/company-logs/{log_id}`에 넣으면 스냅샷을 조회합니다.
   로그 `request_id`는 변경 당시 요청이며 `meta.request_id`는 현재 조회 요청입니다.
4. 항목이 여러 개일 때 `limit=1`로 조회하고,
   `meta.page.next_cursor`를 같은 회사의 다음 요청에 복사합니다.
   첫 페이지는 cursor를 생략합니다. 잘못된 cursor의 실패 테스트 방법은 파라미터 설명을 따릅니다.
5. DELETE로 테스트 회사를 정리합니다(204, 본문 없음).
   이후 회사 단건은404지만 원래 UUID의 이력은 남습니다.
   같은 코드로 재생성하면 새 UUID를 받으며 이력도 분리됩니다.

고정 응답 UUID·시각은 설명용이며 실제 레코드를 만들지 않습니다.
500 예제는 예상하지 못한 서버 장애의 응답 형식이며 의도적인 장애 유발 요청은 제공하지 않습니다.
"""
