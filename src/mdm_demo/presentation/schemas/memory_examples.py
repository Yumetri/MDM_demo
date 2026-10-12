"""Executable Memory examples with status, setup and cleanup instructions."""

from typing import Any

from mdm_demo.presentation.schemas.examples import (
    LIMIT_EXAMPLES as LIMIT_EXAMPLES,
)
from mdm_demo.presentation.schemas.examples import (
    example,
    request_example,
)
from mdm_demo.presentation.schemas.examples import (
    responses as responses,
)

MEMORY_ID = "11111111-1111-4111-8111-111111111111"
LOG_ID = "22222222-2222-4222-8222-222222222222"
REQUEST_ID = "33333333-3333-4333-8333-333333333333"
CHANGE_REQUEST_ID = "44444444-4444-4444-8444-444444444444"
MISSING_ID = "00000000-0000-4000-8000-000000000000"
META = {"request_id": REQUEST_ID}
MEMORY = {
    "id": MEMORY_ID,
    "capacity": 256,
    "unit": "GB",
    "code": "256GB",
    "created_at": "2026-10-12T00:00:00Z",
    "updated_at": "2026-10-12T00:00:00Z",
}
SNAPSHOT = {key: MEMORY[key] for key in ("id", "capacity", "unit", "code")}
UPDATED_SNAPSHOT = {**SNAPSHOT, "capacity": 512, "code": "512GB"}
TB_SNAPSHOT = {**SNAPSHOT, "capacity": 1, "unit": "TB", "code": "1TB"}
GB_SNAPSHOT = {**SNAPSHOT, "capacity": 1000, "unit": "GB", "code": "1000GB"}
LOG = {
    "id": LOG_ID,
    "memory_id": MEMORY_ID,
    "operation": "create",
    "occurred_at": "2026-10-12T00:00:00Z",
    "request_id": CHANGE_REQUEST_ID,
    "before": None,
    "after": SNAPSHOT,
}

CREATE_EXAMPLES = {
    "create_gb": request_example(
        "201 · 256GB · 자동 코드",
        {"capacity": 256, "unit": "GB"},
        201,
        "256GB가 없어야 합니다. code를 보내지 마세요. 응답 data.id로 DELETE "
        "/memories/{memory_id} 정리. 재실행은 MEMORY_CAPACITY_DUP"
        "LICATE/409.",
    ),
    "create_second": request_example(
        "201 · 512GB · 두 번째 항목",
        {"capacity": 512, "unit": "GB"},
        201,
        "512GB가 없어야 합니다. 목록 cursor 및 중복 수정 준비에 사용하고 응답 UUID로 정리하세요.",
    ),
    "create_tb": request_example(
        "201 · 1TB · 환산 기준 1000GB",
        {"capacity": 1, "unit": "TB"},
        201,
        "1TB/1000GB가 없어야 합니다. 표기·중복 예제 준비용. UUID로 정리.",
    ),
    "trim_unit": request_example(
        "201 · 단위 양끝 공백·소문자 정규화",
        {"capacity": 128, "unit": " gb "},
        201,
        "128GB가 없어야 합니다. unit=GB, code=128GB로 저장하며 응답 UUID로 정리하세요.",
    ),
    "minimum": request_example(
        "201 · 용량 하한 1",
        {"capacity": 1, "unit": "GB"},
        201,
        "1GB가 없어야 합니다. 응답 UUID로 정리하세요.",
    ),
    "maximum": request_example(
        "201 · 용량 상한 · TB 환산 넘침 없음",
        {"capacity": 2147483647, "unit": "TB"},
        201,
        "같은 용량이 없어야 합니다. 코드=2147483647TB. 응답 UUID로 정리.",
    ),
    "duplicate_exact": request_example(
        "409 · 같은 256GB 중복",
        {"capacity": 256, "unit": "gb"},
        409,
        "먼저 create_gb 실행. MEMORY_CAPACITY_DUPLICATE. 준비 항목만 UUID로 정리하세요.",
    ),
    "duplicate_equivalent": request_example(
        "409 · 1TB와 1000GB는 중복",
        {"capacity": 1000, "unit": "GB"},
        409,
        "먼저 create_tb 실행. MEMORY_CAPACITY_DUPLICATE. 준비 항목만 UUID로 정리하세요.",
    ),
}
INVALID_INPUTS = {
    "zero": ("용량 0", {"capacity": 0, "unit": "GB"}),
    "negative": ("음수 용량", {"capacity": -1, "unit": "GB"}),
    "over_maximum": ("상한 초과", {"capacity": 2147483648, "unit": "GB"}),
    "string_capacity": ("문자열 용량", {"capacity": "256", "unit": "GB"}),
    "float_capacity": ("실수는 정수로 변환하지 않음", {"capacity": 256.5, "unit": "GB"}),
    "boolean_capacity": ("불리언 용량", {"capacity": True, "unit": "GB"}),
    "null_capacity": ("null 용량", {"capacity": None, "unit": "GB"}),
    "array_capacity": ("배열 용량", {"capacity": [256], "unit": "GB"}),
    "missing_capacity": ("용량 생략", {"unit": "GB"}),
    "missing_unit": ("단위 생략", {"capacity": 256}),
    "null_unit": ("null 단위", {"capacity": 256, "unit": None}),
    "wrong_unit_type": ("단위는 문자열", {"capacity": 256, "unit": 1}),
    "empty_unit": ("빈 단위", {"capacity": 256, "unit": ""}),
    "blank_unit": ("공백 단위", {"capacity": 256, "unit": "  "}),
    "unsupported_unit": ("MB 미지원", {"capacity": 256, "unit": "MB"}),
    "internal_space": ("단위 내부 공백", {"capacity": 256, "unit": "G B"}),
    "empty_body": ("빈 객체", {}),
    "null_body": ("null 본문", None),
    "manual_code": ("코드 입력 금지", {"capacity": 256, "unit": "GB", "code": "CUSTOM"}),
    "null_code": ("null 코드도 입력 금지", {"capacity": 256, "unit": "GB", "code": None}),
    "name_field": ("이름 필드 없음", {"capacity": 256, "unit": "GB", "name": "Storage"}),
    "derived_field": ("환산값 직접 입력 금지", {"capacity": 256, "unit": "GB", "capacity_gb": 256}),
    "extra_field": ("알 수 없는 필드", {"capacity": 256, "unit": "GB", "memo": "demo"}),
}
for key, (summary, value) in INVALID_INPUTS.items():
    CREATE_EXAMPLES[key] = request_example(
        f"422 · {summary}", value, 422, "VALIDATION_ERROR. 데이터·이력이 생성되지 않습니다."
    )

CHANGE_EXAMPLES = {
    "change": request_example(
        "200 · 256GB → 512GB · 코드 갱신",
        {"capacity": 512, "unit": "GB"},
        200,
        "create_gb의 UUID 사용. 512GB가 없어야 함. 코드 갱신·UUID 유지.",
    ),
    "no_change": request_example(
        "200 · 같은 표기 · 시각·이력 유지",
        {"capacity": 256, "unit": " gb "},
        200,
        "현재 256GB인 항목에서 실행. 다른 항목에서는 실제 변경입니다.",
    ),
    "equivalent_representation": request_example(
        "200 · 1TB → 1000GB · 표기 변경 이력",
        {"capacity": 1000, "unit": "GB"},
        200,
        "create_tb의 UUID 사용. 코드·시각·이력 갱신. 자기 자신은 중복 아님.",
    ),
    "duplicate_update": request_example(
        "409 · 다른 항목의 용량으로 수정",
        {"capacity": 512, "unit": "GB"},
        409,
        "create_gb와 create_second를 실행한 뒤 256GB의 UUID에서 요청. "
        "MEMORY_CAPACITY_DUPLICATE이며 원본·시각·이력 유지. 준비 항목 둘 다"
        " 정리하세요.",
    ),
    "duplicate_equivalent_update": request_example(
        "409 · 다른 항목 1TB와 동치인 1000GB",
        {"capacity": 1000, "unit": "GB"},
        409,
        "create_gb와 create_tb를 실행한 뒤 256GB의 UUID에서 요청. MEMO"
        "RY_CAPACITY_DUPLICATE. 준비 항목 둘 다 정리하세요.",
    ),
}
for key, (summary, value) in INVALID_INPUTS.items():
    CHANGE_EXAMPLES[key] = request_example(
        f"422 · {summary}",
        value,
        422,
        "먼저 생성 응답 data.id를 경로에 넣습니다. VALIDATION_ERROR이며 원본·시각·이력 유지.",
    )


def id_examples(kind: str, *, success_status: int = 200, log_list: bool = False) -> dict[str, Any]:
    return {
        "replace_with_actual_id": request_example(
            f"{success_status} · 실제 UUID로 교체",
            LOG_ID if kind == "log" else MEMORY_ID,
            success_status,
            "고정 UUID의 존재를 가정하지 않습니다. "
            + (
                "Memory 이력 목록 data[].id를 복사하세요."
                if kind == "log"
                else "POST /memories의 data.id 복사. 삭제 후 이력도 원래 UUID 사용."
            )
            + " 다른 입력도 해당 요청의 정상 조건을 충족해야 합니다.",
        ),
        "missing": request_example(
            "200 · 기록 없는 Memory UUID" if log_list else "404 · 없는 대상 UUID",
            MISSING_ID,
            200 if log_list else 404,
            "이 UUID의 기록이 없어야 합니다. "
            + ("이력 목록은 빈 배열입니다." if log_list else "NOT_FOUND."),
        ),
        "invalid": request_example("422 · 잘못된 UUID", "not-a-uuid", 422, "VALIDATION_ERROR."),
    }


CURSOR_DESCRIPTION = (
    "첫 페이지는 cursor를 보내지 마세요(빈 문자열도 400). 다음 페이지는 동일 목록 응답의 "
    "meta.page.next_cursor를 그대로 복사하세요. 다른 차원·목록·Memory UUID의 cursor는 "
    "400 INVALID_CURSOR입니다. limit 변경은 허용합니다. 실패 테스트 때만 "
    "cursor=not-a-cursor 또는 cursor=를 수동으로 추가하세요(400 INVALID_CURSOR). "
    "기본 요청의 자동 입력을 막기 위해 고정 cursor 예제는 제공하지 않습니다."
)
MEMORY_SUCCESS = {
    "memory": example("성공 · UUID·시각은 실제 응답 사용", {"data": MEMORY, "meta": META})
}
EMPTY_PAGE = {"data": [], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}}
MEMORY_LIST_SUCCESS = {
    "last_page": example(
        "200 · 마지막 페이지",
        {"data": [MEMORY], "meta": {**META, "page": {"next_cursor": None, "has_next": False}}},
    ),
    "empty": example("200 · 빈 목록", EMPTY_PAGE),
}
LOG_SUCCESS = {
    "created": example("생성 · before=null", {"data": LOG, "meta": META}),
    "updated": example(
        "수정 · 정수 용량·코드 갱신",
        {
            "data": {**LOG, "operation": "update", "before": SNAPSHOT, "after": UPDATED_SNAPSHOT},
            "meta": META,
        },
    ),
    "representation": example(
        "표기 변경 · 1TB→1000GB",
        {
            "data": {**LOG, "operation": "update", "before": TB_SNAPSHOT, "after": GB_SNAPSHOT},
            "meta": META,
        },
    ),
    "deleted": example(
        "삭제 · after=null",
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
    "empty": example("200 · 기록 없는 Memory UUID", EMPTY_PAGE),
}
