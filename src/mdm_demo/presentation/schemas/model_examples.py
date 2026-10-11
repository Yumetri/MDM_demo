"""Executable OpenAPI examples; messages come from the shared error catalog."""

from typing import Any

from mdm_demo.presentation.schemas.examples import example, request_example

MODEL_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
MODEL = {
    "id": MODEL_ID,
    "name": "Galaxy S24",
    "code": "GAL",
    "created_at": "2026-10-10T00:00:00Z",
    "updated_at": "2026-10-10T00:00:00Z",
}
SNAPSHOT = {key: MODEL[key] for key in ("id", "name", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "name": "Galaxy S24 Ultra"}
LOG = {
    "id": LOG_ID,
    "model_id": MODEL_ID,
    "operation": "create",
    "occurred_at": "2026-10-10T00:00:00Z",
    "request_id": CHANGE_REQUEST_ID,
    "before": None,
    "after": SNAPSHOT,
}


CREATE_EXAMPLES = {
    "auto_code": request_example(
        "201 · 코드 생략 → GAL",
        {"name": "Galaxy S24"},
        201,
        "GAL 코드가 없을 때 성공. 재실행하면 DIMENSION_AUTO_CODE_DUPLICATE/409. "
        "정리는 응답 data.id로 DELETE /models/{model_id}.",
    ),
    "manual_code": request_example(
        "201 · 한글 이름 + 소문자 코드 → ABC",
        {"name": "갤럭시", "code": "abc"},
        201,
        "ABC 코드가 없어야 합니다. 이름은 중복 허용, 코드는 중복 불가.",
    ),
    "trim_name": request_example(
        "201 · 이름 양끝만 공백 제거",
        {"name": "  Example  Model  ", "code": "TST"},
        201,
        "TST가 없어야 합니다. 내부 두 칸 공백은 보존합니다.",
    ),
    "name_boundary": request_example(
        "201 · 이름 길이 상한 100자",
        {"name": "가" * 100, "code": "MAX"},
        201,
        "MAX 코드가 없어야 합니다.",
    ),
    "duplicate_manual": request_example(
        "409 · 직접 입력 코드 중복",
        {"name": "Another", "code": "gal"},
        409,
        "먼저 auto_code 예제를 실행해 GAL을 생성합니다. MODEL_CODE_DUPLICATE.",
    ),
    "duplicate_auto": request_example(
        "409 · 자동 생성 코드 중복",
        {"name": "Galaxy S25"},
        409,
        "먼저 auto_code 예제로 GAL을 생성합니다. DIMENSION_AUTO_CODE_DUPLICATE.",
    ),
    "auto_unavailable": request_example(
        "422 · 영문·숫자 부족 → 자동 생성 불가",
        {"name": "LG"},
        422,
        "DIMENSION_AUTO_CODE_UNAVAILABLE. 코드를 직접 입력하면 생성 가능.",
    ),
    "null_code": request_example(
        "422 · null은 생략이 아님",
        {"name": "Galaxy S24", "code": None},
        422,
        "VALIDATION_ERROR. 자동 생성은 code 필드 자체를 생략해야 합니다.",
    ),
    "empty_code": request_example(
        "422 · 빈 코드는 자동 생성 아님",
        {"name": "Galaxy S24", "code": ""},
        422,
        "VALIDATION_ERROR.",
    ),
    "space_code": request_example(
        "201 · 코드 양끝 공백 제거 → S24",
        {"name": "Galaxy S24", "code": " s24 "},
        201,
        "S24 코드가 없어야 합니다.",
    ),
    "non_ascii_code": request_example(
        "422 · 전각 영문 코드 불가",
        {"name": "Galaxy S24", "code": "ＡＢＣ"},
        422,
        "VALIDATION_ERROR. ASCII 영문·숫자 3자만 허용.",
    ),
    "blank_name": request_example(
        "422 · 공백만 있는 이름", {"name": "   ", "code": "ABC"}, 422, "VALIDATION_ERROR."
    ),
    "long_name": request_example(
        "422 · 이름 101자", {"name": "가" * 101, "code": "ABC"}, 422, "VALIDATION_ERROR."
    ),
    "extra_field": request_example(
        "422 · 알 수 없는 필드",
        {"name": "Galaxy S24", "code": "ABC", "memo": "허용되지 않는 필드"},
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
        {"name": "Galaxy S24 Ultra"},
        200,
        "먼저 POST로 생성하고 반환된 data.id를 경로에 넣습니다. 코드는 유지됩니다.",
    ),
    "no_change": request_example(
        "200 · 동일 이름 → 시각·이력 유지",
        {"name": " Galaxy S24 "},
        200,
        "현재 이름이 Galaxy S24인 모델에서 실행합니다. 다르면 일반 이름 변경입니다.",
    ),
    "unicode": request_example("200 · 한글·이모지 이름", {"name": "갤럭시🙂"}, 200),
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
        "422 · 이름 101자", {"name": "가" * 101}, 422, "VALIDATION_ERROR."
    ),
}


def id_examples(kind: str, *, success_status: int = 200) -> dict[str, Any]:
    return {
        "replace_with_actual_id": request_example(
            f"{success_status} · 실제 응답 UUID로 교체",
            LOG_ID if kind == "log" else MODEL_ID,
            success_status,
            "고정 예시 UUID는 DB에 존재한다고 가정하지 않습니다. "
            + (
                "모델별 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /models의 data.id를 복사하세요. "
                "삭제 후에도 이력 경로에서는 같은 UUID를 사용합니다."
            )
            + " 다른 입력도 각 API의 정상 조건을 충족해야 합니다."
            + (" 삭제 성공 시 응답 본문은 없습니다." if success_status == 204 else ""),
        ),
        "missing": example(
            "기록 없는 UUID",
            MISSING_ID,
            "이 UUID의 기록이 없다는 전제입니다. 이력 목록은200 빈 배열, "
            "모델·로그 단건/수정/삭제는404 NOT_FOUND.",
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
    "다른 목록/다른 모델의 cursor는400 INVALID_CURSOR. limit 변경은 가능합니다. "
    "실패 테스트를 할 때만 직접 cursor=not-a-cursor 또는 cursor=를 추가하세요(400 INVALID_CURSOR). "
    "기본 요청에 실패 값이 자동 입력되지 않도록 이 파라미터에는 고정 예제를 넣지 않습니다."
)


MODEL_SUCCESS = {
    "model": example("성공 · 실제 UUID와 시각은 실행 시 생성", {"data": MODEL, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
MODEL_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [MODEL], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
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
    "empty": example("200 · 기록 없는 모델 UUID", EMPTY_PAGE),
}

CREATE_EXAMPLES.update(
    {
        "numeric_auto": request_example(
            "201 · 숫자 포함 자동 생성 → S24",
            {"name": "갤럭시 S24"},
            201,
            "S24 코드가 없어야 합니다.",
        ),
        "blank_code": request_example(
            "422 · 공백만 있는 코드",
            {"name": "Galaxy S24", "code": "   "},
            422,
            "VALIDATION_ERROR.",
        ),
        "internal_space": request_example(
            "422 · 코드 내부 공백", {"name": "Galaxy S24", "code": "S 24"}, 422, "VALIDATION_ERROR."
        ),
        "short_code": request_example(
            "422 · 코드 2자", {"name": "Galaxy S24", "code": "S2"}, 422, "VALIDATION_ERROR."
        ),
        "long_code": request_example(
            "422 · 코드 4자", {"name": "Galaxy S24", "code": "S240"}, 422, "VALIDATION_ERROR."
        ),
    }
)
