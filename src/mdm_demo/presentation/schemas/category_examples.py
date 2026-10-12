"""Executable OpenAPI examples; messages come from the shared error catalog."""

from typing import Any

from mdm_demo.presentation.schemas.examples import example, request_example

CATEGORY_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
CATEGORY = {
    "id": CATEGORY_ID,
    "name": "SMARTPHONE",
    "code": "SMA",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: CATEGORY[key] for key in ("id", "name", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "name": "SMART DEVICES"}
LOG = {
    "id": LOG_ID,
    "category_id": CATEGORY_ID,
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
            LOG_ID if kind == "log" else CATEGORY_ID,
            success_status,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "분류별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /categories의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            )
            + " 다른 입력도 각 API의 정상 조건을 충족해야 합니다."
            + (" 삭제 성공 시 응답 본문은 없습니다." if success_status == 204 else ""),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은200 빈 배열, "
            "분류·로그 단건/수정/삭제는404 NOT_FOUND.",
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
    "다른 목록/다른 분류의 cursor는400 INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor 또는 "
    "cursor=를 추가하세요(400 INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


CATEGORY_SUCCESS = {
    "category": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": CATEGORY, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
CATEGORY_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [CATEGORY], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
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
    "empty": example("200 · 기록 없는 분류 UUID", EMPTY_PAGE),
}

CREATE_EXAMPLES = {
    "manual_code": request_example(
        "201 · 이름·코드 정규화",
        {"name": " smartphone ", "code": " sma "},
        201,
        "SMARTPHONE 이름과 SMA 코드가 없어야 합니다. 응답은 SMARTPHONE/SMA. "
        "재실행 전 해당 항목을 DELETE로 정리하세요.",
    ),
    "second_category": request_example(
        "201 · 두 번째 분류",
        {"name": "Tablet", "code": "TAB"},
        201,
        "TABLET/TAB이 없어야 합니다. 페이지 순회와 수정 중복 예제의 사전 조건입니다.",
    ),
    "unicode_nfc": request_example(
        "201 · 한글 자모 NFC 정규화",
        {"name": "스마트폰", "code": "ABC"},
        201,
        "스마트폰 이름·ABC 코드가 없어야 합니다. 저장 이름은 스마트폰.",
    ),
    "internal_spaces": request_example(
        "201 · 내부 공백 유지",
        {"name": " Example  Category ", "code": "TST"},
        201,
        "EXAMPLE  CATEGORY/TST가 없어야 합니다.",
    ),
    "minimum_name": request_example(
        "201 · 이름 하한 1자", {"name": "a", "code": "MIN"}, 201, "A/MIN이 없어야 합니다."
    ),
    "name_boundary": request_example(
        "201 · 정규화 후 100자",
        {"name": "ß" * 50, "code": "MAX"},
        201,
        "대문자 변환 후 S 100자입니다. 같은 이름과 MAX 코드가 없어야 합니다.",
    ),
    "duplicate_name": request_example(
        "409 · 분류명 중복",
        {"name": " Smartphone ", "code": "NEW"},
        409,
        "먼저 manual_code 실행. NEW 코드는 없어야 합니다. CATEGORY_NAME_DUPLICATE.",
    ),
    "duplicate_code": request_example(
        "409 · 분류 코드 중복",
        {"name": "Other", "code": "sma"},
        409,
        "먼저 manual_code 실행. OTHER 이름은 없어야 합니다. CATEGORY_CODE_DUPLICATE.",
    ),
}

for key, label, body in [
    ("missing_name", "이름 생략 불가", {"code": "SMA"}),
    ("null_code", "null 코드", {"name": "Smartphone", "code": None}),
    ("empty_code", "빈 코드", {"name": "Smartphone", "code": ""}),
    ("blank_code", "공백 코드", {"name": "Smartphone", "code": "  "}),
    ("short_code", "코드 2자", {"name": "Smartphone", "code": "KR"}),
    ("long_code", "코드 4자", {"name": "Smartphone", "code": "SMAE"}),
    ("internal_code_space", "코드 내부 공백", {"name": "Smartphone", "code": "K R"}),
    ("non_ascii_code", "전각 영문 불가", {"name": "Smartphone", "code": "ＫＯＲ"}),
    ("null_name", "null 이름", {"name": None, "code": "SMA"}),
    ("empty_name", "빈 이름", {"name": "", "code": "SMA"}),
    ("blank_name", "공백 이름", {"name": "  ", "code": "SMA"}),
    ("long_name", "이름 101자", {"name": "가" * 101, "code": "SMA"}),
    ("expanded_name", "대문자화 후 102자", {"name": "ß" * 51, "code": "SMA"}),
    ("wrong_name_type", "이름 타입 오류", {"name": 123, "code": "SMA"}),
    ("wrong_code_type", "코드 타입 오류", {"name": "Smartphone", "code": 123}),
    ("extra_field", "알 수 없는 필드", {"name": "Smartphone", "code": "SMA", "memo": "example"}),
]:
    CREATE_EXAMPLES[key] = request_example(
        "422 · " + label,
        body,
        422,
        "VALIDATION_ERROR. 코드 생략만 자동 생성이며 null·빈 값은 거부합니다.",
    )

RENAME_EXAMPLES = {
    "rename": request_example(
        "200 · 분류명 변경",
        {"name": "Smart Devices"},
        200,
        "생성 응답 data.id를 사용하세요. SMART DEVICES 이름은 없어야 합니다. 코드는 유지됩니다.",
    ),
    "no_change": request_example(
        "200 · 정규화 후 동일 이름",
        {"name": " smartphone "},
        200,
        "manual_code로 만든 SMARTPHONE UUID에서 실행. 데이터·시각·이력 유지.",
    ),
    "unicode": request_example(
        "200 · 한글 이름", {"name": "스마트폰"}, 200, "스마트폰 이름은 없어야 합니다."
    ),
    "duplicate_name": request_example(
        "409 · 다른 분류명으로 수정",
        {"name": " tablet "},
        409,
        "manual_code와 second_category를 생성하고 "
        "SMARTPHONE UUID에서 실행. "
        "CATEGORY_NAME_DUPLICATE.",
    ),
}
for key, label, body in [
    ("immutable_code", "코드 수정 불가", {"name": "New", "code": "NEW"}),
    ("empty_body", "빈 객체", {}),
    ("null_name", "null 이름", {"name": None}),
    ("empty_name", "빈 이름", {"name": ""}),
    ("blank_name", "공백 이름", {"name": "  "}),
    ("long_name", "정규화 후 길이 초과", {"name": "ß" * 51}),
    ("wrong_type", "이름 타입 오류", {"name": 123}),
]:
    RENAME_EXAMPLES[key] = request_example(
        "422 · " + label, body, 422, "존재하는 Category UUID에서 실행. VALIDATION_ERROR."
    )


CREATE_EXAMPLES.update(
    {
        "auto_code": request_example(
            "201 · 코드 생략 → SMA",
            {"name": "Smartphone"},
            201,
            "SMARTPHONE 이름·SMA 코드가 없어야 합니다. "
            "manual_code와 같은 항목이므로 둘 중 하나만 실행하세요. "
            "정리는 생성 응답 "
            "data.id로 DELETE /categories/{category_id}.",
        ),
        "numeric_code": request_example(
            "201 · 영문·숫자 코드",
            {"name": "Notebook", "code": " n01 "},
            201,
            "NOTEBOOK 이름·N01 코드가 없어야 합니다.",
        ),
        "numeric_auto": request_example(
            "201 · 숫자를 포함한 자동 생성 → S24",
            {"name": "분류 S24"},
            201,
            "분류 S24 이름·S24 코드가 없어야 합니다.",
        ),
        "duplicate_auto": request_example(
            "409 · 자동 코드 중복",
            {"name": "Smartwatch"},
            409,
            "먼저 auto_code 또는 manual_code로 "
            "SMARTPHONE/SMA를 생성하세요. SMARTWATCH 이름은 "
            "없어야 합니다. "
            "DIMENSION_AUTO_CODE_DUPLICATE.",
        ),
        "auto_unavailable": request_example(
            "422 · 자동 생성 불가",
            {"name": "스마트폰"},
            422,
            "DIMENSION_AUTO_CODE_UNAVAILABLE. 직접 코드를 입력하면 생성할 수 있습니다.",
        ),
        "short_auto": request_example(
            "422 · 자동 생성 문자 2자",
            {"name": "A1"},
            422,
            "DIMENSION_AUTO_CODE_UNAVAILABLE. ASCII 영문·숫자가 3자 이상 필요합니다.",
        ),
        "nul_name": request_example(
            "422 · NUL 이름", {"name": "A\u0000B", "code": "NUL"}, 422, "VALIDATION_ERROR."
        ),
    }
)
