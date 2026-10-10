# API 응답·오류·페이지네이션 규약

Company 구현에 사용하는 계약을 확정했다. 인증·권한 및 다른 차원의 상세 계약은 이번 구현 범위 밖이다. 공통 카탈로그의 인증 오류는 프레임워크 오류 변환을 위한 정의이며 인증 기능 구현을 의미하지 않는다.

## 성공 응답

단건은 `data` 객체와 `meta.request_id`, 목록은 `data` 배열과 `meta.request_id`, `meta.page`를 반환한다.

```json
{
  "data": [{"id": "UUID", "name": "Samsung", "code": "SAM", "created_at": "2026-10-10T00:00:00Z", "updated_at": "2026-10-10T00:00:00Z"}],
  "meta": {
    "request_id": "UUID",
    "page": {"next_cursor": "opaque-token", "has_next": true}
  }
}
```

- 빈 목록은 `data: []`이다. 마지막 페이지는 `next_cursor: null`, `has_next: false`이다.
- 생성은 201, 조회·수정은 200, 삭제는 204이다. 204에는 본문을 넣지 않는다.
- 서버가 매 요청에 새 UUID request ID를 부여한다. 성공·오류의 meta, `X-Request-ID` 응답 헤더, 서버 로그, 변경 이력에서 같은 값을 사용한다. 204는 헤더로 추적한다. 클라이언트의 요청 ID 헤더는 채택하지 않는다.
- 시각은 UTC를 나타내는 ISO 8601 문자열이다. 식별자는 UUID v4다.

## Company 요청·응답

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/companies` | JSON `name` 필수, `code` 생략 가능 | 201 단건 |
| GET `/companies` | 선택적 query `cursor`, `limit` | 200 목록 |
| GET `/companies/{company_id}` | UUID 식별자 | 200 단건 |
| PATCH `/companies/{company_id}` | JSON `name` 필수 | 200 단건 |
| DELETE `/companies/{company_id}` | UUID 식별자 | 204 |

- 응답 필드: `id`, `name`, `code`, `created_at`, `updated_at`.
- `name`은 문자열만 받는다. 양끝 공백을 제거한 후 1~200자여야 하며 내부 공백을 보존한다. PostgreSQL text에서 허용하지 않는 NUL과 UTF-8로 표현할 수 없는 단독 surrogate는 검증 오류(422)다. 정상 한글·이모지와 JSON에서 올바른 surrogate pair로 표현한 문자는 허용한다.
- 직접 코드 입력은 ASCII 영문 3자만 허용하고 대문자로 정규화한다. 공백을 제거해 주지 않는다. 생략만 자동 생성이며 명시적인 null·빈 문자열·공백 포함 입력은 422다.
- 알 수 없는 JSON 필드는 422다. PATCH의 `code` 입력 및 빈 객체도 거부한다. 이름이 같으면 성공 응답하되 데이터·수정 시각·이력은 변경하지 않는다.
- 존재하지 않는 대상과 이미 삭제된 대상의 재삭제는 404다. UUID 형식이 잘못된 경로 값은 422다.
- 검색·선택 정렬 쿼리는 제공하지 않는다. 정의하지 않은 query 파라미터는 FastAPI 기본 동작에 따라 무시되며 조회 조건으로 사용하지 않는다.
- 별도 멱등성 키·버전 필드는 없다. 동시 수정은 행 잠금 순서대로 처리되어 나중 요청의 값이 최종 값이 된다.

## CompanyLog 조회

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| GET `/companies/{company_id}/logs` | 원래 Company UUID, 선택적 query `cursor`, `limit` | 200 이력 목록 |
| GET `/company-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- 로그 응답은 `id`, `company_id`, `operation`, `occurred_at`, `request_id`, `before`, `after`다. operation은 `create`·`update`·`delete`이고 스냅샷은 `id/name/code`다. 생성 전·삭제 후는 null이다.
- 응답 `meta.request_id`는 현재 조회 요청, 로그의 `request_id`는 변경 당시 요청을 가리킨다.
- 회사별 목록은 Company 존재 여부를 검사하지 않는다. 삭제된 회사의 이력도 조회하며, 기록 없는 UUID는 빈 목록(200)이다. 없는 로그 단건은 404, 잘못된 UUID는 422다.
- 목록은 `(occurred_at ASC, id ASC)`로 고정하며 기본 20개, 허용 범위 1~100이다. 시각·UUID 순서가 실제 commit 순서를 보장하지는 않는다. 총 개수·스냅샷 일관성은 제공하지 않는다.
- 로그 cursor는 Company 목록과 구분하고 회사 UUID에 묶는다. 다른 회사 또는 다른 목록의 cursor는 `INVALID_CURSOR`/400이다. 같은 회사에서 limit 변경은 허용한다.
- 로그를 직접 생성·수정·삭제하는 API와 전체 회사의 통합 이력 목록·검색은 제공하지 않는다. 인증·권한은 이번 범위 밖이다.

## Cursor 페이지네이션

- 선택적 `cursor`와 `limit`을 받는다. 기본 `limit=20`, 범위 1~100이고 범위를 벗어나면 422다.
- Company 정렬은 `(created_at ASC, id ASC)`로 고정한다. 이름 변경은 정렬에 영향을 주지 않는다.
- OFFSET을 사용하지 않는다. 마지막 반환 항목의 경계값보다 큰 구간을 `limit + 1`개 조회한다. 경계 행이 삭제돼도 cursor를 계속 사용할 수 있다.
- 토큰에는 버전, Company 조회·정렬 식별자, 경계 시각·UUID를 담고 HMAC-SHA256으로 서명한다. base64url 인코딩은 암호화가 아니며 비밀정보를 담지 않는다. 클라이언트는 해석·구성에 의존하지 않는다.
- 잘못된 형식·변조·지원하지 않는 버전·조회 조건 불일치는 `INVALID_CURSOR`/400이다. 빈 cursor도 잘못된 형식이다.
- limit 변경은 허용한다. 필터·정렬 계약을 추가할 때에는 조회 식별자에 포함해 다른 조건의 cursor를 거부한다.
- 만료 시각은 없다. 서명 키를 교체하면 기존 cursor는 무효다. `CURSOR_SIGNING_KEY`는 최소 32바이트이며 설정이 없거나 짧으면 앱 시작에 실패한다. Compose는 로컬 전용 기본값을 제공한다.
- cursor는 접근 권한이나 사용자 식별 수단이 아니다. 향후 인증·필터 도입 시 매 요청에 해당 정책을 적용해야 한다.
- 총 개수와 스냅샷 일관성을 제공하지 않는다. 순회 중 삭제된 항목은 사라지고, 삽입된 항목은 현재 경계 이후인 경우 뒤 페이지에 나타날 수 있다. 이전 경계에 삽입·commit된 행은 이번 순회에서 누락될 수 있다.

## 오류 응답

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 값이 올바르지 않습니다.",
    "details": [{"field": "query.limit", "code": "OUT_OF_RANGE", "message": "1 이상 100 이하의 값을 입력해 주세요."}]
  },
  "meta": {"request_id": "UUID"}
}
```

- code는 안정적인 분기 식별자이며 message는 중앙 카탈로그의 한국어 기본 문구다. 다국어는 제공하지 않는다.
- details는 배열이고 추가 정보가 없으면 `[]`이다. field가 없는 상세 항목은 null을 사용할 수 있다.
- 프레임워크 검증 상세는 `INVALID_VALUE`와 `입력 값의 형식과 허용 범위를 확인해 주세요.`를 사용한다. limit 범위 위반은 예시의 `OUT_OF_RANGE`를 사용한다.
- 애플리케이션 오류에 필드가 있으면 상세에 동일 오류 코드·메시지와 필드 위치를 넣는다. 위치는 `body.name`, `body.code` 등이다.
- SQL·스택·내부 예외 문자열·비밀정보·원본 입력값을 응답에 넣지 않는다. HTTP 오류 변환에서도 Allow·WWW-Authenticate 같은 의미 있는 헤더를 보존한다.

## 오류 카탈로그

| 코드 | HTTP | 기본 메시지 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 요청 값이 올바르지 않습니다. |
| `INVALID_CURSOR` | 400 | 페이지 커서가 올바르지 않습니다. |
| `BAD_REQUEST` | 400 | 요청을 처리할 수 없습니다. |
| `UNAUTHENTICATED` | 401 | 인증이 필요합니다. |
| `FORBIDDEN` | 403 | 이 작업을 수행할 권한이 없습니다. |
| `NOT_FOUND` | 404 | 요청한 대상을 찾을 수 없습니다. |
| `METHOD_NOT_ALLOWED` | 405 | 지원하지 않는 요청 방식입니다. |
| `CONFLICT` | 409 | 현재 상태에서는 요청을 처리할 수 없습니다. |
| `INTERNAL_ERROR` | 500 | 요청 처리 중 오류가 발생했습니다. |
| `COMPANY_CODE_DUPLICATE` | 409 | 이미 존재하는 회사 코드입니다. |
| `DIMENSION_AUTO_CODE_DUPLICATE` | 409 | 자동 생성된 코드가 이미 존재합니다. 코드를 직접 입력해 주세요. |
| `DIMENSION_AUTO_CODE_UNAVAILABLE` | 422 | {dimension}에서 코드를 자동으로 생성할 수 없습니다. 코드를 직접 입력해 주세요. |

Company는 `{dimension}`에 `company`를 사용한다. 자동 생성 실패의 기존 합의 메시지를 유지했다. 도메인 오류는 application 오류로 변환한 뒤 presentation에서 HTTP로 매핑한다. 알려진 Company 코드 UNIQUE 위반만 코드 중복으로 취급하고 예상하지 못한 DB 오류는 INTERNAL_ERROR로 처리한다.

## 구현·변경 절차

- Scalar `/docs`에서 이름 있는 요청·응답·경로·쿼리 예제를 선택할 수 있다. 각 예제의 예상 상태·사전 조건과 문서 상단 Introduction의 HTTP 테스트 순서를 따른다. 고정 UUID는 설명용이고, 정상 cursor는 실제 응답의 `meta.page.next_cursor`에서 복사한다. 첫 페이지 기본 요청에는 cursor를 포함하지 않는다. cursor는 자동 입력되는 고정 예제 없이 파라미터 설명에 실패 입력의 수동 실행 방법을 안내한다.
- 예제 원본은 [OpenAPI 예제](../src/mdm_demo/presentation/schemas/examples.py)이며 공통 오류 메시지는 카탈로그를 참조한다. [예제 실행 테스트](../tests/api/test_openapi_examples.py)는 OpenAPI에서 꺼낸 실제 요청 예제를 실행하고 null·빈 객체 및 응답 형태 보존을 확인한다.

- [공통 스키마](../src/mdm_demo/presentation/schemas/common.py), [카탈로그](../src/mdm_demo/presentation/error_catalog.py), [예외 처리기](../src/mdm_demo/presentation/exception_handlers.py)를 재사용한다.
- [Company API 테스트](../tests/api/test_company.py)와 [cursor 테스트](../tests/unit/application/test_cursor.py)로 계약을 검증한다. 구체적인 응답 모델은 OpenAPI에 노출한다.
- 필드·코드·메시지·상태·페이지네이션 변경 시 이 문서, 구현, OpenAPI, 계약 테스트를 함께 갱신한다. 공개 계약의 의미를 변경할 때는 호환성 영향과 전환 방법을 기록한다.
