# Executable Year OpenAPI examples using shared catalog helpers.

from typing import Any

from mdm_demo.presentation.schemas.examples import example, request_example

YEAR_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
YEAR = {
    "id": YEAR_ID,
    "year": 2024,
    "code": "2024",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: YEAR[key] for key in ("id", "year", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "year": 2025, "code": "2025"}
LOG = {
    "id": LOG_ID,
    "year_id": YEAR_ID,
    "operation": "create",
    "occurred_at": "2026-10-10T00:00:00Z",
    "request_id": CHANGE_REQUEST_ID,
    "before": None,
    "after": SNAPSHOT,
}


def id_examples(kind: str, *, success_status: int = 200) -> dict[str, Any]:
    return {
        "replace_with_actual_id": request_example(
            f"{success_status} · 실제 응답 UUID로 교체",
            LOG_ID if kind == "log" else YEAR_ID,
            success_status,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "출시 연도별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /years의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            )
            + " 다른 입력도 각 API의 정상 조건을 충족해야 합니다."
            + (" 삭제 성공 시 응답 본문은 없습니다." if success_status == 204 else ""),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은200 빈 배열, "
            "출시 연도·로그 단건/수정/삭제는404 NOT_FOUND.",
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
    "다른 목록/다른 출시 연도의 cursor는400 "
    "INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor"
    " 또는 cursor=를 추가하세요(400 "
    "INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


YEAR_SUCCESS = {
    "year": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": YEAR, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
YEAR_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [YEAR], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
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
    "empty": example("200 · 기록 없는 출시 연도 UUID", EMPTY_PAGE),
}


CREATE_EXAMPLES = {
    "auto_code": request_example(
        "201 · 출시 연도 → 자동 코드",
        {"year": 2024},
        201,
        "2024가 없어야 합니다. 재실행은 "
        "YEAR_DUPLICATE/409. 정리는 응답 data.id로"
        " DELETE /years/{year_id}.",
    ),
    "minimum": request_example(
        "201 · 하한 1900",
        {"year": 1900},
        201,
        "1900이 없어야 합니다. 생성한 UUID로 삭제해 정리합니다.",
    ),
    "maximum": request_example(
        "201 · 상한 2999",
        {"year": 2999},
        201,
        "2999가 없어야 합니다. 미래 연도 허용. 생성한 UUID로 삭제해 정리합니다.",
    ),
    "duplicate": request_example(
        "409 · 연도 중복",
        {"year": 2024},
        409,
        "auto_code로 2024를 먼저 생성합니다. YEAR_DUPLICATE.",
    ),
}
INVALID_INPUTS = {
    "missing_year": {},
    "null_year": {"year": None},
    "string_year": {"year": "2024"},
    "float_year": {"year": 2024.5},
    "boolean_year": {"year": True},
    "below_minimum": {"year": 1899},
    "above_maximum": {"year": 3000},
    "blank_year": {"year": "   "},
    "empty_year": {"year": ""},
    "manual_code": {"year": 2024, "code": "2024"},
    "null_code": {"year": 2024, "code": None},
    "empty_code": {"year": 2024, "code": ""},
    "extra_field": {"year": 2024, "name": "2024년"},
    "null_body": None,
    "array_body": [],
    "scalar_body": 2024,
}
INVALID_LABELS = {
    "missing_year": "필수 year 생략",
    "null_year": "null 연도",
    "string_year": "문자열 연도",
    "float_year": "실수 연도",
    "boolean_year": "boolean 연도",
    "below_minimum": "1900 미만",
    "above_maximum": "2999 초과",
    "blank_year": "공백 문자열",
    "empty_year": "빈 문자열",
    "manual_code": "코드 직접 입력 금지",
    "null_code": "code null도 입력 금지",
    "empty_code": "빈 code도 입력 금지",
    "extra_field": "알 수 없는 필드",
    "null_body": "null 본문",
    "array_body": "배열 본문",
    "scalar_body": "숫자 본문",
}
CREATE_EXAMPLES.update(
    {
        key: request_example(
            f"422 · {INVALID_LABELS[key]}",
            value,
            422,
            "VALIDATION_ERROR. year 정수 1900~2999만 받습니다. code를 포함한 추가 필드는 불허.",
        )
        for key, value in INVALID_INPUTS.items()
    }
)
CHANGE_EXAMPLES = {
    "change": request_example(
        "200 · 2024 → 2025, 코드도 재생성",
        {"year": 2025},
        200,
        "2024를 생성한 data.id를 경로에 넣으세요. 2025가 "
        "없어야 합니다. UUID 유지. 생성한 UUID로 삭제해 "
        "정리합니다.",
    ),
    "no_change": request_example(
        "200 · 같은 연도 → 시각·이력 유지",
        {"year": 2024},
        200,
        "현재 2024인 UUID에서 실행합니다. 다른 연도라면 실제 변경입니다.",
    ),
    "duplicate": request_example(
        "409 · 이미 등록한 연도로 변경",
        {"year": 2025},
        409,
        "2024·2025를 각각 생성하고 2024의 UUID에서 "
        "실행하세요. YEAR_DUPLICATE. 실패 시 데이터·이력 "
        "유지. 두 UUID로 삭제해 정리합니다.",
    ),
    "minimum": request_example(
        "200 · 하한으로 변경", {"year": 1900}, 200, "생성 응답 UUID 사용. 1900이 없어야 합니다."
    ),
    "maximum": request_example(
        "200 · 상한으로 변경", {"year": 2999}, 200, "생성 응답 UUID 사용. 2999가 없어야 합니다."
    ),
}
CHANGE_EXAMPLES.update(
    {
        key: request_example(
            f"422 · {INVALID_LABELS[key]}",
            value,
            422,
            "존재하는 Year UUID에서 실행하세요. VALIDATION_ERROR. 실패 시 데이터·이력 유지.",
        )
        for key, value in INVALID_INPUTS.items()
    }
)


for examples in (CREATE_EXAMPLES, CHANGE_EXAMPLES):
    examples["float_year"]["description"] += (
        " Scalar는 2024.0을 2024로 직렬화하므로 실행 예제는 2024.5를 사용합니다."
        ' 2024.0도 거부됩니다. 원문 JSON {"year":2024.0}을 Raw 본문으로 보내 확인하세요.'
    )
