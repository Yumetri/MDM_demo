"""Executable OpenAPI examples; messages come from the shared error catalog."""

from typing import Any

from mdm_demo.presentation.schemas.examples import example, request_example

COUNTRY_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
COUNTRY = {
    "id": COUNTRY_ID,
    "name": "KOREA",
    "code": "KOR",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: COUNTRY[key] for key in ("id", "name", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "name": "REPUBLIC OF KOREA"}
LOG = {
    "id": LOG_ID,
    "country_id": COUNTRY_ID,
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
            LOG_ID if kind == "log" else COUNTRY_ID,
            success_status,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "국가별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /countries의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            )
            + " 다른 입력도 각 API의 정상 조건을 충족해야 합니다."
            + (" 삭제 성공 시 응답 본문은 없습니다." if success_status == 204 else ""),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은200 빈 배열, "
            "국가·로그 단건/수정/삭제는404 NOT_FOUND.",
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
    "다른 목록/다른 국가의 cursor는400 INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor 또는 cursor=를 추가하세요(400 INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


COUNTRY_SUCCESS = {
    "country": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": COUNTRY, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
COUNTRY_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [COUNTRY], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
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
    "empty": example("200 · 기록 없는 국가 UUID", EMPTY_PAGE),
}

CREATE_EXAMPLES = {
    "manual_code": request_example(
        "201 · 이름·코드 정규화",
        {"name": " korea ", "code": " kor "},
        201,
        "KOREA 이름과 KOR 코드가 없어야 합니다. 응답은 KOREA/KOR. "
        "재실행 전 해당 항목을 DELETE로 정리하세요.",
    ),
    "second_country": request_example(
        "201 · 두 번째 국가",
        {"name": "Japan", "code": "JPN"},
        201,
        "JAPAN/JPN이 없어야 합니다. 페이지 순회와 수정 중복 예제의 사전 조건입니다.",
    ),
    "unicode_nfc": request_example(
        "201 · 한글 자모 NFC 정규화",
        {"name": "대한민국", "code": "ABC"},
        201,
        "대한민국 이름·ABC 코드가 없어야 합니다. 저장 이름은 대한민국.",
    ),
    "internal_spaces": request_example(
        "201 · 내부 공백 유지",
        {"name": " Example  Country ", "code": "TST"},
        201,
        "EXAMPLE  COUNTRY/TST가 없어야 합니다.",
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
        "409 · 국가명 중복",
        {"name": " Korea ", "code": "NEW"},
        409,
        "먼저 manual_code 실행. NEW 코드는 없어야 합니다. COUNTRY_NAME_DUPLICATE.",
    ),
    "duplicate_code": request_example(
        "409 · 국가 코드 중복",
        {"name": "Other", "code": "kor"},
        409,
        "먼저 manual_code 실행. OTHER 이름은 없어야 합니다. COUNTRY_CODE_DUPLICATE.",
    ),
}

for key, label, body in [
    ("missing_code", "코드 생략 불가", {"name": "Korea"}),
    ("missing_name", "이름 생략 불가", {"code": "KOR"}),
    ("null_code", "null 코드", {"name": "Korea", "code": None}),
    ("empty_code", "빈 코드", {"name": "Korea", "code": ""}),
    ("blank_code", "공백 코드", {"name": "Korea", "code": "  "}),
    ("numeric_code", "숫자 불가", {"name": "Korea", "code": "K01"}),
    ("short_code", "코드 2자", {"name": "Korea", "code": "KR"}),
    ("long_code", "코드 4자", {"name": "Korea", "code": "KORE"}),
    ("internal_code_space", "코드 내부 공백", {"name": "Korea", "code": "K R"}),
    ("non_ascii_code", "전각 영문 불가", {"name": "Korea", "code": "ＫＯＲ"}),
    ("null_name", "null 이름", {"name": None, "code": "KOR"}),
    ("empty_name", "빈 이름", {"name": "", "code": "KOR"}),
    ("blank_name", "공백 이름", {"name": "  ", "code": "KOR"}),
    ("long_name", "이름 101자", {"name": "가" * 101, "code": "KOR"}),
    ("expanded_name", "대문자화 후 102자", {"name": "ß" * 51, "code": "KOR"}),
    ("wrong_name_type", "이름 타입 오류", {"name": 123, "code": "KOR"}),
    ("wrong_code_type", "코드 타입 오류", {"name": "Korea", "code": 123}),
    ("extra_field", "알 수 없는 필드", {"name": "Korea", "code": "KOR", "memo": "example"}),
]:
    CREATE_EXAMPLES[key] = request_example(
        "422 · " + label, body, 422, "VALIDATION_ERROR. 자동 생성은 제공하지 않습니다."
    )

RENAME_EXAMPLES = {
    "rename": request_example(
        "200 · 국가명 변경",
        {"name": "Republic of Korea"},
        200,
        "생성 응답 data.id를 사용하세요. "
        "REPUBLIC OF KOREA 이름은 없어야 합니다. 코드는 유지됩니다.",
    ),
    "no_change": request_example(
        "200 · 정규화 후 동일 이름",
        {"name": " korea "},
        200,
        "manual_code로 만든 KOREA UUID에서 실행. 데이터·시각·이력 유지.",
    ),
    "unicode": request_example(
        "200 · 한글 이름", {"name": "대한민국"}, 200, "대한민국 이름은 없어야 합니다."
    ),
    "duplicate_name": request_example(
        "409 · 다른 국가명으로 수정",
        {"name": " japan "},
        409,
        "manual_code와 second_country를 생성하고 KOREA UUID에서 실행. COUNTRY_NAME_DUPLICATE.",
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
        "422 · " + label, body, 422, "존재하는 Country UUID에서 실행. VALIDATION_ERROR."
    )
