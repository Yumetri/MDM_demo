"""Executable OpenAPI examples; messages come from the shared error catalog."""

from typing import Any

from mdm_demo.presentation.schemas.examples import example, request_example

NETWORK_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
NETWORK = {
    "id": NETWORK_ID,
    "name": "LTE",
    "code": "LTE",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: NETWORK[key] for key in ("id", "name", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "name": "LTE ADVANCED"}
LOG = {
    "id": LOG_ID,
    "network_id": NETWORK_ID,
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
            LOG_ID if kind == "log" else NETWORK_ID,
            success_status,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "규격별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /networks의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            )
            + " 다른 입력도 각 API의 정상 조건을 충족해야 합니다."
            + (" 삭제 성공 시 응답 본문은 없습니다." if success_status == 204 else ""),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은 200 빈 배열, "
            "규격·로그 단건/수정/삭제는 404 NOT_FOUND.",
        ),
        "invalid": example("422 · UUID 형식 오류", "not-a-uuid", "VALIDATION_ERROR."),
    }


LIMIT_EXAMPLES = {
    "small_page": example(
        "200 · 페이지 순회 확인", 1, "항목이 2개 이상이면 다음 cursor가 반환됩니다."
    ),
    "default_page": example("200 · 기본 크기", 20),
    "max_page": example("200 · 최대 크기", 100),
    "zero": example("422 · 하한 미만", 0, "VALIDATION_ERROR / OUT_OF_RANGE."),
    "too_large": example("422 · 상한 초과", 101, "VALIDATION_ERROR / OUT_OF_RANGE."),
    "wrong_type": example("422 · 정수 아님", "many", "VALIDATION_ERROR / INVALID_VALUE."),
}
CURSOR_DESCRIPTION = (
    "첫 페이지는 cursor를 보내지 마세요(빈 문자열도 400). 다음 페이지는 같은 목록 응답의 "
    "meta.page.next_cursor를 그대로 복사하세요. "
    "서명·경계값은 서버가 생성하며 고정 정상 예제는 없습니다. "
    "다른 목록/다른 규격의 cursor는 400 INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor 또는 cursor=를 추가하세요(400 INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


NETWORK_SUCCESS = {
    "network": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": NETWORK, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
NETWORK_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [NETWORK], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
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
    "empty": example("200 · 기록 없는 규격 UUID", EMPTY_PAGE),
}


CREATE_EXAMPLES = {
    "auto_code": request_example(
        "201 · 코드 생략 → LTE",
        {"name": " lte "},
        201,
        "LTE 이름·코드가 없어야 합니다. 재실행은 409이며 NETWORK_NAME_DUPLICATE "
        "또는 DIMENSION_AUTO_CODE_DUPLICATE입니다. 오류 우선순위는 보장하지 않습니다. "
        "정리는 반환된 data.id로 DELETE /networks/{network_id}.",
    ),
    "manual_code": request_example(
        "201 · 직접 코드와 이름 정규화",
        {"name": "5G NR", "code": " nr5g "},
        201,
        "5G NR 이름·NR5G 코드가 없어야 합니다. 저장 값은 5G "
        "NR/NR5G. 실행 후 필요하면 반환 UUID로 삭제합니다.",
    ),
    "second_network": request_example(
        "201 · 두 번째 규격",
        {"name": "5G"},
        201,
        "5G 이름·코드가 없어야 합니다. 최신순 페이지와 수정 중복 테스트의 사전 조건입니다.",
    ),
    "extract_all": request_example(
        "201 · 기호 제거 후 전체 추출",
        {"name": "LTE-A"},
        201,
        "LTE-A 이름·LTEA 코드가 없어야 합니다. 3자로 자르지 않습니다.",
    ),
    "unicode_nfc": request_example(
        "201 · 한글 자모 NFC 정규화",
        {"name": "이동통신", "code": "MOBILE"},
        201,
        "이동통신 이름·MOBILE 코드가 없어야 합니다. 한글만으로 자동 "
        "생성은 불가하므로 직접 입력합니다.",
    ),
    "internal_spaces": request_example(
        "201 · 내부 공백 보존",
        {"name": " Example  Network ", "code": "TST"},
        201,
        "EXAMPLE  NETWORK 이름·TST 코드가 없어야 합니다.",
    ),
    "minimum_code": request_example(
        "201 · 이름·코드 하한 1자", {"name": "a", "code": "a"}, 201, "A 이름·코드가 없어야 합니다."
    ),
    "maximum_code": request_example(
        "201 · 코드 20자",
        {"name": "B" * 20},
        201,
        "이름·코드 B 20자가 없어야 합니다. 자동 생성 상한입니다.",
    ),
    "name_boundary": request_example(
        "201 · 정규화 후 이름 100자",
        {"name": "ß" * 50, "code": "MAX"},
        201,
        "이름 S 100자·MAX 코드가 없어야 합니다. 자동 추출은 20자 "
        "초과이므로 직접 코드를 입력합니다.",
    ),
    "duplicate_name": request_example(
        "409 · 규격명 중복",
        {"name": " LTE ", "code": "NEW"},
        409,
        "먼저 auto_code로 LTE 생성. NEW 코드가 없어야 합니다. NETWORK_NAME_DUPLICATE.",
    ),
    "duplicate_code": request_example(
        "409 · 직접 코드 중복",
        {"name": "Other", "code": "lte"},
        409,
        "먼저 auto_code로 LTE 생성. OTHER 이름은 없어야 합니다. NETWORK_CODE_DUPLICATE.",
    ),
    "duplicate_auto": request_example(
        "409 · 자동 코드 충돌",
        {"name": "L T E"},
        409,
        "먼저 auto_code로 LTE 생성. L T E 이름은 없어야 합니다. "
        "DIMENSION_AUTO_CODE_DUPLICATE. code를 직접 입력하면 등록할 수 "
        "있습니다.",
    ),
    "auto_unavailable": request_example(
        "422 · 추출 가능한 문자 없음",
        {"name": "이동통신"},
        422,
        "DIMENSION_AUTO_CODE_UNAVAILABLE. 직접 코드를 입력하세요.",
    ),
    "auto_too_long": request_example(
        "422 · 자동 코드 21자",
        {"name": "C" * 21},
        422,
        "DIMENSION_AUTO_CODE_UNAVAILABLE. 자르지 않으므로 직접 코드를 입력하세요.",
    ),
}
for key, label, body in [
    ("missing_name", "이름 생략", {"code": "LTE"}),
    ("null_code", "null은 생략이 아님", {"name": "LTE", "code": None}),
    ("empty_code", "빈 코드", {"name": "LTE", "code": ""}),
    ("blank_code", "공백 코드", {"name": "LTE", "code": "  "}),
    ("long_code", "직접 코드 21자", {"name": "LTE", "code": "A" * 21}),
    ("internal_code_space", "코드 내부 공백", {"name": "LTE", "code": "L TE"}),
    ("code_symbol", "코드 기호", {"name": "LTE", "code": "LTE-A"}),
    ("non_ascii_code", "전각 코드", {"name": "LTE", "code": "ＬＴＥ"}),
    ("null_name", "null 이름", {"name": None}),
    ("empty_name", "빈 이름", {"name": ""}),
    ("blank_name", "공백 이름", {"name": "  "}),
    ("long_name", "이름 101자", {"name": "가" * 101, "code": "MAX"}),
    ("expanded_name", "대문자화 후 이름 102자", {"name": "ß" * 51, "code": "MAX"}),
    ("nul_name", "저장 불가능한 NUL", {"name": "A\u0000B", "code": "AB"}),
    ("wrong_name_type", "이름 타입", {"name": 123}),
    ("wrong_code_type", "코드 타입", {"name": "LTE", "code": 123}),
    ("extra_field", "알 수 없는 필드", {"name": "LTE", "memo": "example"}),
]:
    CREATE_EXAMPLES[key] = request_example(
        "422 · " + label, body, 422, "VALIDATION_ERROR. 상태 변경·이력 추가 없음."
    )

RENAME_EXAMPLES = {
    "rename": request_example(
        "200 · 규격명 변경",
        {"name": "LTE Advanced"},
        200,
        "auto_code 생성 응답 data.id를 사용하세요. LTE "
        "ADVANCED 이름은 없어야 합니다. 코드는 LTE로 유지합니다.",
    ),
    "no_change": request_example(
        "200 · 정규화 후 동일 이름",
        {"name": " lte "},
        200,
        "auto_code로 만든 LTE UUID에서 실행. 데이터·수정 시각·이력 유지.",
    ),
    "unicode": request_example(
        "200 · 자유 등록 이름",
        {"name": "이동통신"},
        200,
        "이동통신 이름이 없어야 합니다. 등록 코드는 유지합니다.",
    ),
    "duplicate_name": request_example(
        "409 · 다른 규격명으로 수정",
        {"name": " 5g "},
        409,
        "auto_code·second_network 실행 후 LTE UUID에서 요청하세요. NETWORK_NAME_DUPLICATE.",
    ),
}
for key, label, body in [
    ("immutable_code", "코드 수정 금지", {"name": "New", "code": "NEW"}),
    ("empty_body", "빈 객체", {}),
    ("null_name", "null 이름", {"name": None}),
    ("empty_name", "빈 이름", {"name": ""}),
    ("blank_name", "공백 이름", {"name": "  "}),
    ("long_name", "이름 101자", {"name": "가" * 101}),
    ("expanded_name", "정규화 후 102자", {"name": "ß" * 51}),
    ("nul_name", "NUL 이름", {"name": "A\u0000B"}),
    ("wrong_type", "이름 타입", {"name": 123}),
    ("extra_field", "알 수 없는 필드", {"name": "New", "memo": "example"}),
]:
    RENAME_EXAMPLES[key] = request_example(
        "422 · " + label,
        body,
        422,
        "먼저 auto_code로 생성한 실제 Network UUID에서 실행. VALIDATION_ERROR. 상태·이력 유지.",
    )
