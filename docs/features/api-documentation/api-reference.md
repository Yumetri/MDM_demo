# API 문서 제공

## 제공 기능

- 사용자와 목적: 개발자가 API 명세를 열람하고 Scalar UI에서 요청을 실행한다. 도구는 OpenAPI 스키마를 조회할 수 있다.
- 처리 결과: 문서 UI의 HTML 또는 OpenAPI JSON을 제공한다.
- 진입점: Scalar UI `GET /docs`, OpenAPI 스키마 `GET /openapi.json`.
- API 계약: [API 규약](../../api-conventions.md)은 Company와 공통 응답·오류 계약을 관리한다. 각 기능의 구현 범위는 해당 기능 문서에서 확인한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 구현 근거 |
| --- | --- | --- |
| 브라우저에서 문서 UI 사용 | Scalar 번들 CDN 접근 필요 | [app.py — add_scalar_reference()](../../../src/mdm_demo/app.py) |
| API 명세 열람 | 애플리케이션의 OpenAPI 스키마 사용 | [app.py — app](../../../src/mdm_demo/app.py) |
| 문서 UI 구성 | Swagger UI·ReDoc, Scalar 에이전트·텔레메트리는 설정에서 비활성화 | [app.py — FastAPI(), add_scalar_reference()](../../../src/mdm_demo/app.py) |

## 처리 흐름

1. `/docs`가 Scalar 초기화 설정을 포함한 HTML을 반환한다.
2. 브라우저가 외부 번들과 `/openapi.json`을 불러와 명세를 표시한다.
3. UI에서 요청을 실행하면 선택한 API가 해당 요청을 처리한다.

## 데이터와 트랜잭션

사용하지 않음. 문서 제공 자체에는 DB·Aggregate 접근이나 데이터 변경이 없다. UI에서 실행하는 개별 API의 데이터 처리는 해당 기능 문서에서 관리한다.

## 조회와 인덱스

사용하지 않음. 문서 제공에는 DB 조회·인덱스·cursor 페이지네이션이 없다.

## 캐시

- Redis 등 별도 업무 캐시는 사용하지 않는다.
- FastAPI는 생성한 OpenAPI 스키마를 애플리케이션 인스턴스의 `app.openapi_schema`에 보관한다. 요청별 키나 TTL은 없으며 인스턴스 메모리 범위에서 재사용한다.
- 설치된 FastAPI의 `FastAPI.openapi()`는 스키마가 없거나 라우트 버전이 바뀌면 다시 생성한다. 이 프로젝트에는 별도 캐시 갱신·무효화·장애 fallback 로직이 없다.
- DB 커밋과의 연계는 없다. 브라우저·CDN의 HTTP 캐시 정책은 이 저장소에서 별도로 설정하지 않으며 미확인이다.
- 근거: [app.py](../../../src/mdm_demo/app.py)의 기본 FastAPI 생성 설정과 [uv.lock](../../../uv.lock)으로 고정한 `fastapi.applications.FastAPI.openapi()` 구현.

## 구현과 검증

| 구분 | 위치 | 역할·확인하는 동작 |
| --- | --- | --- |
| 구현 | [app.py — FastAPI()](../../../src/mdm_demo/app.py) | OpenAPI 제공 설정 |
| 구현 | [app.py — add_scalar_reference()](../../../src/mdm_demo/app.py) | Scalar 라우트·번들·UI 설정 |
| 검증 | [smoke.py — check_api_docs()](../../../scripts/smoke.py) | Scalar 초기화 코드와 스키마 경로, 헬스 응답 정의, 문서 UI의 OpenAPI 작업 목록 제외, 기존 문서 경로 비활성화 확인 |

- 검증 진입점: [Makefile](../../../Makefile)의 `make smoke`. 실행 전제와 번들 버전 관리 위치는 [프로젝트 README](../../../README.md)를 따른다.
- 실제 브라우저에서 Company 생성·조회·수정·삭제 요청과 응답을 확인했다. [API 계약 테스트](../../../tests/api/test_company.py)는 구체적인 OpenAPI 스키마도 검사한다.
- Company CRUD·CompanyLog 조회에 성공·실패·경계값 요청/응답과 경로·쿼리 예제를 제공한다. 각 예제는 상태·사전 조건을 설명하고 동적인 UUID·cursor 복사 절차를 안내한다. [예제 테스트](../../../tests/api/test_openapi_examples.py)는 OpenAPI 예제를 실제 HTTP 요청으로 실행한다.
- 검증 공백: 스모크 검사는 실제 브라우저 렌더링·CDN 로딩·UI 요청 실행·OpenAPI 메모리 재사용을 검사하지 않는다. 전용 브라우저 자동화 테스트는 없다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [헬스 체크](../operations/health-check.md) | 문서의 요청·응답 정의를 확인하는 스모크 검사에서 사용 |

[API 문서 목차](README.md)
