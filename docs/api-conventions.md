# API 응답·오류·페이지네이션 규약

Company·Model·Brand·Country·Year·Network 구현에 사용하는 계약을 확정했다. 인증·권한 및 다른 차원의 상세 계약은 이번 구현 범위 밖이다. 공통 카탈로그의 인증 오류는 프레임워크 오류 변환을 위한 정의이며 인증 기능 구현을 의미하지 않는다.

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

## Model 요청·응답

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/models` | JSON `name` 필수, `code` 생략 가능 | 201 단건 |
| GET `/models` | 선택적 query `cursor`, `limit` | 200 목록 |
| GET `/models/{model_id}` | UUID 식별자 | 200 단건 |
| PATCH `/models/{model_id}` | JSON `name` 필수 | 200 단건 |
| DELETE `/models/{model_id}` | UUID 식별자 | 204 |

- 응답 필드는 `id`, `name`, `code`, `created_at`, `updated_at`이다. UUID v4와 UTC 시각을 사용한다.
- 모델명은 문자열이며 양끝 공백 제거 후 1~100자다. 내부 공백·한글·기호·이모지를 보존하고 중복을 허용한다. NUL·단독 surrogate는 422다.
- 직접 코드는 양끝 공백을 제거한 뒤 ASCII 영문·숫자 정확히 3자를 대문자로 정규화한다. 내부 공백·기호는 422다. ` s24 `는 `S24`가 된다.
- 코드 필드 생략만 자동 생성이다. 명시적 null·빈 문자열·공백만 있는 문자열·잘못된 타입은 422다. 생성 규칙은 [Model](features/dimension/model.md)을 따른다.
- 알 수 없는 JSON 필드, PATCH의 code·빈 객체는 422다. 같은 이름 수정은 200이며 데이터·수정 시각·이력은 변경하지 않는다.
- 없는 대상·삭제 후 조회·재삭제는 404, 잘못된 UUID는 422다. 삭제는 물리 삭제이며 코드 재사용 시 새 UUID를 부여한다.
- 목록은 `(created_at ASC, id ASC)`, 기본 20개·1~100개이며 공통 cursor 계약을 따른다. 토큰 조회 식별자는 Model 전용이며 Company·다른 목록 cursor를 거부한다.
- 검색·선택 정렬·총 개수·캐시는 제공하지 않는다. 알 수 없는 query 파라미터는 Company와 같이 무시한다.
- 별도 멱등성 키·버전 필드는 없다. 동시 수정·삭제는 행 잠금 획득 후 최신 값을 처리하며 나중 수정이 최종 값이다.

## ModelLog 조회

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| GET `/models/{model_id}/logs` | 원래 Model UUID, 선택적 query `cursor`, `limit` | 200 이력 목록 |
| GET `/model-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- 응답은 `id`, `model_id`, `operation`, `occurred_at`, `request_id`, `before`, `after`다. operation은 `create`·`update`·`delete`, 스냅샷은 `id/name/code`다. 생성 전·삭제 후는 null이다.
- CompanyLog와 동일하게 현재 조회의 `meta.request_id`와 변경 당시 로그의 `request_id`를 구분한다.
- 삭제된 Model의 이력도 조회한다. 기록 없는 UUID는 200 빈 목록, 없는 로그 단건은 404, 잘못된 UUID는 422다.
- `(occurred_at ASC, id ASC)`로 정렬하며 기본 20개·1~100개다. cursor는 대상 Model UUID와 조회·정렬에 묶는다. 다른 Model·다른 차원·다른 목록의 cursor는 `INVALID_CURSOR`/400이다. 동일 목록의 limit 변경은 허용한다.
- 실제 commit 순서·총 개수·스냅샷 일관성은 보장하지 않는다. 로그 직접 생성·수정·삭제 API, 통합 이력 검색, 인증·권한은 제공하지 않는다.

## Brand·BrandLog 요청·응답

아래는 이슈 #4에서 사용자와 합의해 구현·OpenAPI에 반영한 계약이다. 업무 규칙은 [Brand](features/dimension/brand.md)·[BrandLog](features/dimension/brand-log.md)를 따른다.

- Brand 필드는 `id`, `name`, `code`, `created_at`, `updated_at`이다. 입력은 브랜드명과 선택적 코드이며 UUID·시각은 서버에서 부여한다.
- 브랜드명은 양끝 공백 제거 후 1~100자이며 중복을 허용한다. 직접 코드는 양끝 공백 제거 후 ASCII 영문·숫자 3자를 대문자로 저장한다. 코드 생략 시 자동 생성한다.
- 이름만 수정할 수 있으며 코드는 불변이다. 정규화한 이름이 같으면 200으로 성공하고 데이터·수정 시각·로그는 바꾸지 않는다.
- 삭제는 물리 삭제이며 이력을 보존한다. 삭제 코드로 재등록하면 새 UUID를 부여한다.
- `GET /brands/{brand_id}/logs`는 삭제된 Brand의 이력도 조회한다. 기록 없는 UUID는 200 빈 목록을 반환한다.
- `GET /brand-logs/{log_id}`는 이력 단건을 반환하며 존재하지 않는 로그는 404다.
- 이력에는 대상 Brand 식별자와 변경 전·후 `id/name/code`, 작업 종류, 기록 시각, 요청 ID를 포함한다.
- Brand·이력 목록은 cursor 방식이며 기본 20개·최대 100개다. Brand는 생성 시각·UUID 오름차순, 이력은 기록 시각·로그 UUID 오름차순이다.
- Cursor는 목록 종류별로 구분하고 이력 cursor는 해당 Brand UUID에도 묶는다. 다른 목록·다른 대상에 사용할 수 없다.
- 동시 수정·삭제는 행 잠금 획득 후 최신 값을 기준으로 처리한다. 별도의 버전 충돌 검사는 제공하지 않는다.
- 구현 범위는 CRUD·이력 조회다. 인증·권한, 검색·필터, 사용자 지정 정렬, 캐시는 제공하지 않는다. PostgreSQL에서 직접 조회한다.

HTTP 입력·응답·오류 처리는 Model과 동일하게 적용하기로 합의했다. Brand의 경로·식별자·차원별 오류만 아래와 같이 구분한다.

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/brands` | JSON `name` 필수, `code` 생략 가능 | 201 단건 |
| GET `/brands` | 선택적 query `cursor`, `limit` | 200 목록 |
| GET `/brands/{brand_id}` | UUID 식별자 | 200 단건 |
| PATCH `/brands/{brand_id}` | JSON `name` 필수 | 200 단건 |
| DELETE `/brands/{brand_id}` | UUID 식별자 | 204, 본문 없음 |
| GET `/brands/{brand_id}/logs` | UUID 식별자, 선택적 query `cursor`, `limit` | 200 이력 목록 |
| GET `/brand-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- 공통 성공·오류 envelope, 서버 발급 요청 ID, UUID v4·UTC 시각, 요청별 이력 ID 구분은 기존 계약을 따른다. 로그의 `request_id`는 변경 당시 요청, `meta.request_id`는 현재 조회 요청이다.
- 코드 생략만 자동 생성이다. 명시적 null·빈 문자열·공백만 있는 값·잘못된 타입은 422다. 이름의 NUL·단독 surrogate는 거부하고 정상 한글·이모지는 보존한다.
- 알 수 없는 JSON 필드, PATCH의 `code`·빈 객체는 422다. 정의하지 않은 query 파라미터는 기존 Model처럼 무시하며 검색 조건으로 사용하지 않는다.
- 없는 Brand의 단건 조회·수정·삭제, 삭제 후 조회·재삭제는 404다. 잘못된 UUID 형식은 422다. 이력 목록은 앞서 정한 대로 기록 없는 UUID에도 200 빈 목록을 반환한다.
- 이력 응답 필드는 `id`, `brand_id`, `operation`, `occurred_at`, `request_id`, `before`, `after`다. 작업은 `create`·`update`·`delete`이며 생성 전·삭제 후 스냅샷은 null이다.
- `limit` 허용 범위는 1~100이며 범위 밖은 422다. 잘못된 형식·변조·다른 목록 또는 대상의 cursor는 `INVALID_CURSOR`/400이다. 첫 페이지는 cursor를 생략하고 다음 페이지는 실제 응답의 `meta.page.next_cursor`를 사용한다.
- 공통 cursor의 HMAC 서명·키 교체, limit 변경 허용, 경계 행 삭제 후 조회, 총 개수·스냅샷 일관성 미제공 정책을 그대로 적용한다. 로그 정렬은 실제 commit 순서를 보장하지 않는다.

| 오류 코드 | HTTP | 메시지 |
| --- | --- | --- |
| `BRAND_CODE_DUPLICATE` | 409 | 이미 존재하는 브랜드 코드입니다. |
| `DIMENSION_AUTO_CODE_DUPLICATE` | 409 | 기존 공통 카탈로그 메시지 |
| `DIMENSION_AUTO_CODE_UNAVAILABLE` | 422 | 공통 메시지의 `{dimension}`에 `brand` 사용 |

그 밖의 검증·없는 대상·cursor·내부 오류는 기존 공통 카탈로그를 따른다. 알려진 Brand 코드 UNIQUE 위반만 중복으로 변환한다. Brand 오류는 카탈로그·OpenAPI 예제·테스트에 함께 반영했다.

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
| `MEMORY_CAPACITY_DUPLICATE` | 409 | 이미 존재하는 저장공간 용량입니다. |
| `MODEL_CODE_DUPLICATE` | 409 | 이미 존재하는 모델 코드입니다. |
| `BRAND_CODE_DUPLICATE` | 409 | 이미 존재하는 브랜드 코드입니다. |
| `COMPANY_CODE_DUPLICATE` | 409 | 이미 존재하는 회사 코드입니다. |
| `DIMENSION_AUTO_CODE_DUPLICATE` | 409 | 자동 생성된 코드가 이미 존재합니다. 코드를 직접 입력해 주세요. |
| `DIMENSION_AUTO_CODE_UNAVAILABLE` | 422 | {dimension}에서 코드를 자동으로 생성할 수 없습니다. 코드를 직접 입력해 주세요. |

Company는 `{dimension}`에 `company`, Model은 `model`, Brand는 `brand`를 사용한다. 자동 생성 실패의 기존 합의 메시지를 유지했다. 도메인 오류는 application 오류로 변환한 뒤 presentation에서 HTTP로 매핑한다. 각 차원의 알려진 코드 UNIQUE 위반만 코드 중복으로 취급하고 예상하지 못한 DB 오류는 INTERNAL_ERROR로 처리한다.

## 구현·변경 절차

- Scalar `/docs`에서 이름 있는 요청·응답·경로·쿼리 예제를 선택할 수 있다. 각 예제의 예상 상태·사전 조건과 문서 상단 Introduction의 HTTP 테스트 순서를 따른다. 고정 UUID는 설명용이고, 정상 cursor는 실제 응답의 `meta.page.next_cursor`에서 복사한다. 첫 페이지 기본 요청에는 cursor를 포함하지 않는다. cursor는 자동 입력되는 고정 예제 없이 파라미터 설명에 실패 입력의 수동 실행 방법을 안내한다.
- Brand 예제 원본은 [Brand OpenAPI 예제](../src/mdm_demo/presentation/schemas/brand_examples.py)이며 [실행 테스트](../tests/api/test_brand_openapi_examples.py)로 검증한다.
- Model 예제 원본은 [Model OpenAPI 예제](../src/mdm_demo/presentation/schemas/model_examples.py)이며 [실행 테스트](../tests/api/test_model_openapi_examples.py)로 성공·실패·경계값을 검증한다.
- 예제 원본은 [OpenAPI 예제](../src/mdm_demo/presentation/schemas/examples.py)이며 공통 오류 메시지는 카탈로그를 참조한다. [예제 실행 테스트](../tests/api/test_openapi_examples.py)는 OpenAPI에서 꺼낸 실제 요청 예제를 실행하고 null·빈 객체 및 응답 형태 보존을 확인한다.

- [공통 스키마](../src/mdm_demo/presentation/schemas/common.py), [카탈로그](../src/mdm_demo/presentation/error_catalog.py), [예외 처리기](../src/mdm_demo/presentation/exception_handlers.py)를 재사용한다.
- [Company API 테스트](../tests/api/test_company.py)와 [cursor 테스트](../tests/unit/application/test_cursor.py)로 계약을 검증한다. 구체적인 응답 모델은 OpenAPI에 노출한다.
- 필드·코드·메시지·상태·페이지네이션 변경 시 이 문서, 구현, OpenAPI, 계약 테스트를 함께 갱신한다. 공개 계약의 의미를 변경할 때는 호환성 영향과 전환 방법을 기록한다.

## Country 오류 계약

런타임 오류 카탈로그·OpenAPI·테스트에 적용한 Country 전용 계약이다.

| 조건 | 코드 | HTTP | 기본 메시지 |
| --- | --- | --- | --- |
| 정규화된 국가명 중복 | `COUNTRY_NAME_DUPLICATE` | 409 | 이미 존재하는 국가명입니다. |
| 정규화된 국가 코드 중복 | `COUNTRY_CODE_DUPLICATE` | 409 | 이미 존재하는 국가 코드입니다. |
| 입력 형식 오류 | `VALIDATION_ERROR` | 422 | 요청 값이 올바르지 않습니다. |

Country는 코드 자동 생성 기능이 없으므로 자동 생성 전용 오류를 사용하지 않는다. 업무 규칙은 [Country](features/dimension/country.md)를 따른다. HTTP 계약은 아래 절을 따른다.

## Country API 경로

- CRUD: `/countries`, `/countries/{country_id}`.
- 국가별 이력: `/countries/{country_id}/logs`.
- 로그 단건: `/country-logs/{log_id}`.

## Country HTTP 계약

공통 응답·오류·페이지네이션 구조를 재사용한다.

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/countries` | 문자열 `name`, `code` 모두 필수 | 201 단건 |
| GET `/countries` | 선택적 `cursor`, `limit` | 200 목록 |
| GET `/countries/{country_id}` | Country UUID | 200 단건 |
| PATCH `/countries/{country_id}` | 문자열 `name` 필수 | 200 단건 |
| DELETE `/countries/{country_id}` | Country UUID | 204, 본문 없음 |
| GET `/countries/{country_id}/logs` | 원래 Country UUID, 선택적 `cursor`, `limit` | 200 이력 목록 |
| GET `/country-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- Country 응답은 `id/name/code/created_at/updated_at`, 로그 응답은 `id/country_id/operation/occurred_at/request_id/before/after`다. UUID v4·UTC 시각과 기존 공통 `data/meta` 응답을 사용한다.
- 필수 필드 생략·명시적 null·빈 값·공백만 있는 값·잘못된 타입·알 수 없는 JSON 필드는 422다. PATCH의 code 및 빈 객체도 422다.
- 없는 Country 조회·수정·삭제, 삭제 후 조회·재삭제, 없는 로그 단건은 404다. 잘못된 UUID 형식은 422다.
- 이력 목록은 현재 Country 존재를 검사하지 않는다. 기록 없는 UUID는 200 빈 목록이며 삭제한 Country의 기록도 조회한다.
- 목록의 limit은 기본 20, 허용 범위 1~100이다. Country는 (created_at ASC, id ASC), 이력은 (occurred_at ASC, id ASC)로 정렬한다.
- 잘못된·빈·변조된 cursor, 다른 차원·다른 목록·다른 대상 이력의 cursor는 400 INVALID_CURSOR다. 같은 목록에서 limit 변경은 허용한다. 첫 페이지에는 cursor를 생략한다.
- 검색·선택 정렬·총 개수는 제공하지 않는다. 기존 차원처럼 알 수 없는 query 파라미터는 무시한다.
- 이름·코드 중복은 위 합의된 전용 409 오류로 구분한다. 동시에 둘 다 중복인 경우에는 DB가 보고한 알려진 제약에 해당하는 오류 하나를 반환하며 우선순위를 보장하지 않는다.
- 이름 길이는 공백 제거·대문자 변환·NFC 정규화가 끝난 저장 값을 기준으로 판단한다. 공통 오류 details는 name에 body.name, code에 body.code를 사용한다.
- 목록 순회는 총 개수·스냅샷 일관성·실제 commit 순서를 보장하지 않는다. 로그 자동 만료, 행위자 저장, 인증·권한, 멱등성 키·자동 재시도는 이번 범위에서 제외한다.

- Country 생성은 name·code가 필수다. 이름은 trim → 대문자 → NFC 후 1~100자이며 유일하다. NUL·단독 surrogate는 거부한다. 코드는 trim 후 ASCII 영문 3자로 검증하고 대문자로 저장하며 유일하다. 코드 자동 생성·ISO 존재 검증은 하지 않는다.
- PATCH는 name만 받으며 정규화된 이름이 같으면 수정 시각·로그를 변경하지 않는다. 물리 삭제 후 이름·코드 재사용은 새 UUID로 처리한다.
- [Country 예제 원본](../src/mdm_demo/presentation/schemas/country_examples.py)과 [예제 실행 테스트](../tests/api/test_country_openapi_examples.py)로 정상·실패·경계값을 검증한다.

## Category HTTP 계약

2026-10-12 사용자와 합의한 계약을 Category 런타임·OpenAPI·오류 카탈로그·테스트에 반영했다. 업무 규칙은 [Category](features/dimension/category.md), 로그 보존·스냅샷 범위는 [CategoryLog](features/dimension/category-log.md), 구현 계획은 [6번 계획](plans/issue-6-category.md)을 따른다.

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/categories` | 문자열 name 필수, 문자열 code 생략 가능 | 201 단건 |
| GET `/categories` | 선택적 cursor·limit | 200 목록 |
| GET `/categories/{category_id}` | Category UUID | 200 단건 |
| PATCH `/categories/{category_id}` | 문자열 name 필수 | 200 단건 |
| DELETE `/categories/{category_id}` | Category UUID | 204, 본문 없음 |
| GET `/categories/{category_id}/logs` | 원래 Category UUID, 선택적 cursor·limit | 200 이력 목록 |
| GET `/category-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- Category 응답은 id/name/code/created_at/updated_at, 로그 응답은 id/category_id/operation/occurred_at/request_id/before/after다. UUID v4·UTC 시각과 공통 data/meta 응답을 재사용한다.
- 로그의 request_id는 변경 당시 서버 발급 요청 ID, meta.request_id는 현재 조회 요청 ID다. before/after는 id/name/code 스냅샷이며 생성 전·삭제 후에는 null이다.
- name은 필수 문자열이다. 코드 자동 생성은 필드 생략에만 적용한다. 명시적 null·빈 문자열·공백만 있는 값·잘못된 타입·알 수 없는 JSON 필드는 422 VALIDATION_ERROR다.
- PATCH는 name만 받으며 code 입력·빈 객체·알 수 없는 필드는 422다. 정규화 후 이름이 같으면 200을 반환하고 데이터·updated_at·로그를 유지한다.
- 없는 Category의 단건 조회·수정·삭제, 삭제 후 조회·재삭제, 없는 로그 단건은 기존 공통 계약처럼 404 NOT_FOUND다. 잘못된 UUID 형식은 422다.
- 이력 목록은 현재 Category 존재를 검사하지 않는다. 기록 없는 UUID는 200 빈 목록이며 삭제한 Category의 기록도 조회한다.
- Category 목록은 (created_at ASC, id ASC), 이력은 (occurred_at ASC, id ASC)로 정렬한다. limit 기본 20, 범위 1~100이며 범위 위반은 422다.
- 첫 페이지에는 cursor를 생략한다. 다음 페이지는 같은 목록 응답의 meta.page.next_cursor를 사용한다. 같은 목록에서 limit 변경은 허용한다.
- 기존 공통 HMAC cursor 계약을 적용한다. 빈 값·잘못된 형식·변조·다른 차원/목록/대상 이력 cursor는 400 INVALID_CURSOR다. 키 교체 시 기존 cursor가 무효화되며 만료 시각은 없다.
- 검색·사용자 지정 정렬·총 개수는 제공하지 않는다. 기존 차원과 같이 정의하지 않은 query 파라미터는 무시한다. 순회 중 스냅샷 일관성·실제 commit 순서는 보장하지 않는다.
- 오류 details의 필드는 name에 body.name, code에 body.code를 사용한다. 기존 공통 검증·cursor·없는 대상·내부 오류 계약과 입력·내부 정보 비노출 원칙을 재사용한다.

### Category 중복·자동 생성 오류

아래 코드·상태·문구와 동시 중복 우선순위 없음은 최종 계획에서 합의했다. 공통 자동 생성 메시지는 기존 계약을 그대로 재사용한다.

| 조건 | 코드 | HTTP | 기본 메시지 |
| --- | --- | --- | --- |
| 정규화된 이름 중복 | `CATEGORY_NAME_DUPLICATE` | 409 | 이미 존재하는 분류명입니다. |
| 직접 입력한 코드 중복 | `CATEGORY_CODE_DUPLICATE` | 409 | 이미 존재하는 분류 코드입니다. |
| 자동 생성한 코드 중복 | `DIMENSION_AUTO_CODE_DUPLICATE` | 409 | 기존 공통 카탈로그 메시지 |
| 자동 생성에 필요한 영문·숫자 부족 | `DIMENSION_AUTO_CODE_UNAVAILABLE` | 422 | 기존 공통 메시지의 {dimension}에 category 사용 |

- 이름과 코드가 동시에 중복이면 DB가 보고한 알려진 제약에 해당하는 오류 하나를 반환하며 우선순위를 보장하지 않는다.
- 코드 중복은 자동 생성 여부에 따라 위 두 오류를 구분한다. Category 생성·이름 수정의 알려진 UNIQUE 제약만 해당 중복으로 변환하고 예상하지 못한 DB 오류는 공통 INTERNAL_ERROR로 처리한다.

### Category OpenAPI 구현·검증

- 생성·수정 본문, 경로 UUID·로그 UUID, limit에 이름 있는 예제를 제공한다. 예제마다 예상 상태·오류 코드·사전 조건을 적는다.
- 입력 생략/null/빈 값/공백/타입·길이·코드 형식, 정규화된 이름 중복, 직접/자동 코드 중복·자동 생성 불가, 없는 대상·no-op·삭제 후 조회, cursor·limit 경계를 포함한다.
- 두 항목으로 같은 이름 중복만 발생시키는 예제는 서로 다른 유효 코드를 사용한다. 코드 중복만 검사할 때에는 서로 다른 정규화 이름을 사용해 동시 중복의 우선순위 없음에 의존하지 않는다.
- 정상 UUID·서명 cursor는 실제 생성/목록 응답에서 복사하며 고정 UUID 존재를 가정하지 않는다. 중복 예제는 사전 생성·정리 절차를 안내하고 DELETE 204에는 본문 예제를 만들지 않는다.
- 공통 실행 순서는 문서 상단에서 한 번만 안내한다. 첫 페이지 cursor에 실패 예제를 자동 입력하지 않고 수동 실행 방법만 설명한다.
- OpenAPI에서 추출한 실제 요청 예제를 API 테스트로 실행하고 실제 Scalar에서 예제 선택·요청 실행, 첫 페이지 생성 코드와 전송 요청의 cursor 생략을 확인한다.
- [Category 예제 원본](../src/mdm_demo/presentation/schemas/category_examples.py)과 [예제 실행 테스트](../tests/api/test_category_openapi_examples.py)로 요청 예제·null 보존·구체 응답·중복 오류를 검증했다. 실제 Scalar 실행 결과는 [작업 계획](plans/issue-6-category.md)에 기록했다. 단독 surrogate는 문서 JSON에 넣지 않고 실제 API 테스트에서 JSON escape 입력의 거부를 검증한다.

## Year·YearLog HTTP 계약

2026-10-12 사용자와 합의해 런타임·OpenAPI·테스트에 반영한 계약이다. Year는 제품 출시 연도 차원이다. 업무 규칙은 [Year](features/dimension/year.md)·[YearLog](features/dimension/year-log.md), 구현 순서는 [작업 계획](plans/issue-7-year-dimension.md)을 따른다.

### 합의한 입력·변경 정책

- 생성·수정 본문은 필수 `year` 하나만 받는다. JSON 정수 1900~2999만 허용한다.
- 문자열 `"2024"`, 실수 `2024.0`, boolean, null, 필드 생략, 빈 객체·잘못된 본문 타입, 범위 밖 값은 422 `VALIDATION_ERROR`다. 자동 형변환하지 않는다.
- `code`·`name`·알 수 없는 필드는 거부한다. 코드 생략은 서버 자동 생성이며 null·빈 코드도 직접 입력이므로 거부한다.
- 서버는 `year: 2024`에서 `code: "2024"`를 만든다. 연도·코드는 각각 유일하다.
- 수정은 UUID를 유지하고 연도·코드를 함께 변경한다. 중복 연도면 변경·로그 모두 취소한다.
- 같은 연도로 수정하면 200 성공이고 데이터·수정 시각·로그는 그대로다.
- 삭제는 물리 삭제·로그 보존이며 같은 연도 재등록은 새 UUID를 발급한다.
- Year 목록은 연도 내림차순, 이력 목록은 기록 시각·로그 UUID 내림차순이다. 두 목록 모두 기본 20개·허용 1~100개로 합의했다. 초기 데이터는 자동 생성하지 않는다.
- 조회는 단건·고정 정렬 목록·대상별 이력까지 제공하며 검색·연도 범위 필터·총 개수는 제외한다.

### HTTP 경로·응답

| API | 입력 | 성공 응답 |
| --- | --- | --- |
| POST `/years` | 본문 `year` | 201 단건 |
| GET `/years` | 선택적 query `cursor`, `limit` | 200 목록 |
| GET `/years/{year_id}` | UUID 식별자 | 200 단건 |
| PATCH `/years/{year_id}` | UUID, 본문 `year` | 200 단건 |
| DELETE `/years/{year_id}` | UUID 식별자 | 204 본문 없음 |
| GET `/years/{year_id}/logs` | 원래 Year UUID, 선택적 `cursor`, `limit` | 200 이력 목록 |
| GET `/year-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

- 기존 성공·오류 envelope와 서버 발급 request ID를 사용한다.
- Year 응답은 `id/year/code/created_at/updated_at`이다. year는 정수, code는 문자열, 식별자는 UUID v4, 시각은 UTC다.
- 로그 응답은 `id/year_id/operation/occurred_at/request_id/before/after`다. before/after는 `id/year/code` 스냅샷이며 생성 전·삭제 후는 null이다. 원본 생성/수정 시각은 스냅샷에 포함하지 않는다.
- 로그의 request_id는 변경 당시 요청, meta.request_id는 현재 조회 요청이다.
- 없는 Year의 조회·수정·삭제, 삭제 후 조회·재삭제, 없는 로그 단건은 404 `NOT_FOUND`다. 잘못된 UUID는 422다.
- 대상별 이력 목록은 현재 Year 존재를 검사하지 않으며 기록 없는 UUID도 200 빈 목록이다.
- 합의한 목록 정렬은 Year의 유일한 year DESC와 이력의 occurred_at DESC/id DESC다. 이력의 다음 페이지는 (occurred_at, id)가 마지막 경계보다 작은 구간을 조회한다. 기본 20개·허용 1~100개다.
- Year cursor는 정수 연도 경계·조회 종류·정렬에 묶고 다음 페이지는 year가 경계보다 작은 구간을 조회한다. 이력 cursor는 대상 UUID에도 묶는다. 경계 행이 삭제돼도 토큰은 계속 사용하며 같은 목록의 limit 변경을 허용한다.
- 첫 페이지는 cursor를 생략하고 다음 페이지는 실제 응답 meta.page.next_cursor를 복사한다. 고정된 정상 토큰이나 실패 예제를 기본 입력으로 제공하지 않는다.
- 잘못된·빈·변조·다른 목록/차원/대상의 cursor는 400 `INVALID_CURSOR`다. 서명·키 교체·만료 없음 정책은 공통 cursor 규약을 따른다.
- 순회 중 Year 수정·재등록에 따른 이동과 중복·누락, 총 개수·스냅샷 일관성을 보장하지 않는다. 이력 정렬은 실제 commit 순서를 보장하지 않는다.

### 합의한 중복 오류

| 코드 | HTTP | 메시지 | 적용 |
| --- | --- | --- | --- |
| `YEAR_DUPLICATE` | 409 | 이미 존재하는 출시 연도입니다. | 생성·수정에서 알려진 연도/자동 코드 UNIQUE 위반 |

오류 details의 필드는 `body.year`다. 코드를 직접 입력할 수 없으므로 직접 코드 입력을 권하는 `DIMENSION_AUTO_CODE_DUPLICATE` 메시지는 사용하지 않는다. 다른 DB 실패는 중복으로 오인하지 않고 기존 내부 오류로 처리한다. 입력·없는 대상·cursor 오류 메시지는 기존 중앙 카탈로그를 재사용한다.

### 예제·검증 기준

- Scalar는 JavaScript 숫자를 재직렬화하므로 실수 실행 예제는 소수 부분이 남는 2024.5를 사용한다. 2024.0 거부 계약은 원문 JSON 요청과 생성·수정 API 테스트로 별도 확인한다.

- 정상 생성·수정·같은 값 수정, 1900/2999 경계, 1899/3000 범위 오류, 생략/null/문자열/실수/boolean/추가 필드, 직접 code 입력, 생성·수정 중복, 없는 대상·삭제 후 조회·재삭제·재등록을 이름 있는 예제로 제공한다.
- 생성 응답 UUID·이력 응답 UUID·실제 cursor의 복사 위치와 실행 순서를 안내한다. 수정 중복 예제는 두 연도를 먼저 생성하는 준비 절차를 둔다. 예제마다 예상 상태·오류·정리 절차를 기록한다.
- 공통 순서는 문서 상단에 한 번 두고 Year의 준비 사항만 추가한다. 정상 cursor를 가짜 토큰으로 제시하지 않으며 204에는 본문 예제를 만들지 않는다.
- OpenAPI에 노출된 본문·경로·query·응답 예제와 실제 대표 HTTP 응답을 테스트한다. Scalar에서 예제 선택·실행과 첫 페이지 코드/실제 요청의 cursor 생략을 확인한다.

### 구현 범위

독립 차원·Year CRUD·대상별 이력/로그 단건 조회를 제공하며 검색·연도 범위 필터·총 개수와 다른 차원의 FK 연결은 제외하기로 합의했다. 로그는 추가 전용이다.

인증·권한·행위자, 차원 캐시, 로그 통합 검색·자동 만료, 멱등성 키·자동 재시도는 추가하지 않는다. 수정·삭제는 행 잠금으로 직렬 처리하며 별도 낙관적 버전 검사를 추가하지 않는다. 검증 근거는 [Year 검증 보고](reports/issue-7-validation.md)를 따른다.

## Memory/MemoryLog HTTP 계약

2026-10-12 사용자와 확정한 Memory 계약이다. 구현·OpenAPI·관련 테스트에 함께 반영한다. 업무 의미는 [Memory](features/dimension/memory.md)·[MemoryLog](features/dimension/memory-log.md)를 따른다.

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST /memories | JSON capacity·unit 모두 필수 | 201 단건 |
| GET /memories | 선택적 cursor·limit | 200 목록 |
| GET /memories/{memory_id} | Memory UUID | 200 단건 |
| PATCH /memories/{memory_id} | JSON capacity·unit 모두 필수 | 200 단건 |
| DELETE /memories/{memory_id} | Memory UUID | 204, 본문 없음 |
| GET /memories/{memory_id}/logs | 원본 UUID, 선택적 cursor·limit | 200 이력 목록 |
| GET /memory-logs/{log_id} | 로그 UUID | 200 로그 단건 |

- 생성·수정에는 capacity와 unit만 받는다. capacity는 엄격한 JSON 정수 1~2,147,483,647이며 bool·실수·문자열·null을 거부한다. unit은 문자열, trim·대문자 정규화 후 GB 또는 TB만 허용한다. 생략·null·공백만 있는 값·내부 공백·지원하지 않는 단위는 422 VALIDATION_ERROR다.
- code는 항상 서버가 capacity의 10진 정수 문자열 + 정규화한 unit으로 생성한다. 요청의 code·capacity_gb·name 및 알 수 없는 JSON 필드는 422다. PATCH에서 한 필드만 보내거나 빈 객체를 보내는 것도 422다.
- Memory 응답은 id·capacity·unit·code·created_at·updated_at이다. capacity는 정수이며 unit은 GB/TB다. 내부 환산값 capacity_gb는 요청·응답에 노출하지 않는다. UUID v4·UTC 시각·기존 공통 data/meta envelope를 재사용한다.
- 수정은 UUID·created_at을 유지하고 capacity·unit·code를 함께 바꾼다. 1TB → 1000GB는 실제 변경으로 updated_at·로그를 갱신한다. 정규화 후 capacity·unit이 모두 같으면 200을 반환하며 데이터·시각·로그는 유지한다.
- 환산 용량 중복 생성·수정은 MEMORY_CAPACITY_DUPLICATE/409, 메시지는 '이미 존재하는 저장공간 용량입니다.'다. errors.details의 field는 body.capacity이며 세부 code·message는 동일 오류를 사용한다. 알려진 환산 용량·파생 코드 UNIQUE 위반만 이 오류로 변환한다.
- 코드 직접 입력을 안내하는 DIMENSION_AUTO_CODE_DUPLICATE·DIMENSION_AUTO_CODE_UNAVAILABLE는 Memory에 사용하지 않는다.
- 없는 Memory의 단건·수정·삭제, 삭제 후 조회·재삭제, 없는 로그 단건은 404 NOT_FOUND다. 잘못된 UUID는 422 VALIDATION_ERROR다. 이력 목록은 Memory의 현재 존재를 검사하지 않으며 기록 없는 UUID에는 200 빈 목록을 반환한다.
- 로그 응답은 id·memory_id·operation·occurred_at·request_id·before·after다. 스냅샷은 id·capacity·unit·code이며 capacity는 정수다. 작업은 create/update/delete, 생성 전과 삭제 후는 null이다. 로그 request_id는 변경 당시 요청이고 meta.request_id는 현재 조회 요청이다.
- 목록 limit 기본값은 20, 허용 범위는 1~100이다. Memory는 created_at ASC/id ASC, 이력은 occurred_at ASC/id ASC로 정렬한다. limit 변경은 허용한다.
- cursor는 HMAC 서명·Memory 목록/로그 목록/대상 UUID 별 문맥으로 분리한다. 빈 값·형식 오류·변조·다른 차원·목록·대상의 cursor는 INVALID_CURSOR/400이다. 첫 페이지에는 cursor를 생략하고 다음 페이지에는 실제 meta.page.next_cursor를 사용한다. 경계 행 삭제 이후도 경계값으로 조회한다.
- 총 개수·순회 중 스냅샷 일관성·실제 commit 순서는 보장하지 않는다. 검색·필터·사용자 지정 정렬은 제공하지 않으며 알 수 없는 query는 기존 차원처럼 무시한다.
- 인증·권한·캐시는 합의한 범위에서 제외한다. 기존 공통 방식처럼 멱등성 키·자동 재시도·행위자·자동 이력 만료는 추가하지 않는다.
- OpenAPI 이름 있는 예제에 생성·수정·단건·목록·삭제·이력, 타입/범위/단위/필수 필드 오류, GB/TB 동치 중복·중복 수정, no-op·표기 변경·삭제 후 조회를 포함한다. 실제 UUID·cursor의 복사 순서와 상태 의존 예제의 준비·정리를 안내한다. 204는 본문 예제가 없고 선택적 cursor는 기본 예제로 자동 입력하지 않는다.
## Network·NetworkLog HTTP 계약

이슈 #8에서 업무 규칙·공통 HTTP 표현·오류 메시지·운영 기본 정책을 사용자와 합의하고 런타임 오류 카탈로그·OpenAPI·API·테스트에 반영했다.
업무 명세는 [Network](features/dimension/network.md)·[NetworkLog](features/dimension/network-log.md)를 따른다. Company·Model·Brand·Country의 오름차순과 Year의 내림차순 계약은 변경하지 않는다.

| 메서드·경로 | 입력 | 성공 |
| --- | --- | --- |
| POST `/networks` | JSON name 필수, code 생략 가능 | 201 단건 |
| GET `/networks` | 선택 cursor·limit | 200 목록 |
| GET `/networks/{network_id}` | Network UUID | 200 단건 |
| PATCH `/networks/{network_id}` | JSON name 필수 | 200 단건 |
| DELETE `/networks/{network_id}` | Network UUID | 204 본문 없음 |
| GET `/networks/{network_id}/logs` | Network UUID, 선택 cursor·limit | 200 이력 목록 |
| GET `/network-logs/{log_id}` | 로그 UUID | 200 이력 단건 |

### 합의한 입력·동작의 HTTP 계약

- 단건 필드는 id/name/code/created_at/updated_at. UUID v4·UTC·공통 envelope·서버 request ID 정책을 유지한다.
- name은 문자열이며 strip → upper → NFC 후 1~100자, 내부 공백·한글·숫자·기호를 보존하고 정규화한 이름은 유일하다. 길이는 변환 후 판단한다. NUL·단독 surrogate는 기존 차원처럼 422로 거부한다.
- 직접 code는 strip 후 ASCII 영문·숫자 1~20자로 검증하고 대문자로 저장한다. name의 ASCII 영문·숫자 전체 추출로 자동 생성하며 0자·20자 초과·코드 중복은 실패한다. 잘라내거나 접미사를 붙이지 않는다.
- code 필드 생략만 자동 생성이다. 명시 null·빈값·공백만 있는 값·비문자열·내부 공백·기호는 422다. 알 수 없는 JSON 필드, PATCH의 code·빈 객체도 422다.
- PATCH는 name만 변경하며 code는 유지한다. 정규화한 동일 이름 수정은 200이고 데이터·수정 시각·이력 변경이 없다. 수정 이름도 유일성 검사한다.
- 삭제한 이름·코드를 재사용할 수 있으며 새 UUID를 발급한다. 없는 대상·삭제 후 조회·재삭제는 404, 잘못된 UUID 형식은 422다.
- 이력 응답은 id/network_id/operation/occurred_at/request_id/before/after다. create/update/delete와 전체 id/name/code 스냅샷을 반환하며 생성 전·삭제 후는 null이다. 로그 request_id는 변경 당시 요청, meta.request_id는 현재 조회다.
- 대상별 이력은 원본 존재를 확인하지 않고 삭제된 대상도 조회한다. 기록 없는 UUID는 200 빈 목록, 없는 로그 단건은 404다.
- 이력 직접 생성·수정·삭제 API·통합 이력 검색은 제공하지 않으며 자동 만료·행위자 필드를 추가하지 않는다.

### 합의한 최신순 조회와 cursor 계약

- Network 목록 `(created_at DESC, id DESC)`, 이력 목록 `(occurred_at DESC, id DESC)`, 기본 20개·허용 1~100개다. 검색·필터·선택 정렬·총 개수는 제공하지 않는다.
- 다음 페이지는 이전 페이지 마지막 시각·UUID보다 작은 키를 조회한다. 동률은 UUID로 구분한다. 이름 수정은 Network의 목록 위치를 바꾸지 않는다.
- HMAC 서명·길이·정규 인코딩 검증을 기존 방식으로 유지하되 조회 식별자에 Network 및 내림차순을 포함한다. 로그 cursor는 Network UUID에도 묶는다. 다른 목록·차원·대상·정렬의 토큰은 INVALID_CURSOR/400이다. 동일 목록의 limit 변경은 허용한다.
- 첫 페이지는 cursor를 생략한다. 동적 cursor는 실제 응답의 meta.page.next_cursor에서 복사한다. cursor 오류 예제는 기본 요청에 자동 입력하지 않고 설명에서 수동 입력을 안내한다.
- 공통 빈/마지막 페이지 응답을 유지하며 총 개수·스냅샷 일관성을 보장하지 않는다. 순회 중 경계보다 최신인 삽입은 이미 지나간 범위라 누락될 수 있고 삭제한 항목은 사라진다. 실제 commit 순서를 보장하지 않는다.

### 합의한 오류 카탈로그

| 조건 | 코드 | HTTP | 기본 메시지 |
| --- | --- | --- | --- |
| 생성·수정의 이름 중복 | NETWORK_NAME_DUPLICATE | 409 | 이미 존재하는 네트워크 규격명입니다. |
| 직접 코드 중복 | NETWORK_CODE_DUPLICATE | 409 | 이미 존재하는 네트워크 코드입니다. |
| 자동 코드 중복 | DIMENSION_AUTO_CODE_DUPLICATE | 409 | 자동 생성된 코드가 이미 존재합니다. 코드를 직접 입력해 주세요. |
| 자동 추출 결과 없음·20자 초과 | DIMENSION_AUTO_CODE_UNAVAILABLE | 422 | network에서 코드를 자동으로 생성할 수 없습니다. 코드를 직접 입력해 주세요. |

입력·없는 대상·cursor·내부 오류는 기존 공통 오류 카탈로그를 따른다. details.field는 해당 body.name/body.code/query.limit/path 필드를 사용한다. 알려진 이름·코드 UNIQUE 위반만 중복으로 변환한다. 둘 다 중복인 경우 어느 오류가 먼저 반환되는지는 별도 우선순위를 보장하지 않는다.
정의하지 않은 query 파라미터는 기존 차원처럼 무시하며 조회 조건으로 사용하지 않는다. 멱등성 키·자동 재시도·commit 응답 유실 복구는 제공하지 않는다.


Network의 [실행 예제](../src/mdm_demo/presentation/schemas/network_examples.py)에는 31개 생성·14개 수정 본문과 경로·limit·응답 예제를 제공한다. [예제 실행 검사](../tests/api/test_network_openapi_examples.py)는 스키마에서 꺼낸 예제를 실제 요청으로 실행하고 응답 모델·null·cursor 기본 생략·공통 테스트 안내를 검증한다. 실제 Scalar 검수 범위는 [Network](features/dimension/network.md)와 [검수 결과](plans/issue-8-network-dimension.md#구현검수-결과)를 따른다.
