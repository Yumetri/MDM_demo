# 헬스 체크

## 제공 기능

- 사용자와 목적: 운영 도구가 서비스 프로세스의 HTTP 응답 여부를 확인한다.
- 처리 결과: 본문 없는 성공 응답을 반환한다.
- 진입점: `GET /health`.
- API 계약: [API 규약](../../api-conventions.md)은 공통 응답·오류 계약을 관리한다. 현재 응답 정의는 아래 구현과 [OpenAPI](../api-documentation/api-reference.md)에서 확인한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 구현 근거 |
| --- | --- | --- |
| 요청이 핸들러에 도달함 | 별도 업무 조건 없이 응답 | [health.py — health()](../../../src/mdm_demo/presentation/routers/health.py) |
| DB·Redis 상태 확인이 필요함 | 이 엔드포인트에서는 확인하지 않음 | [health.py — health()](../../../src/mdm_demo/presentation/routers/health.py) |

## 처리 흐름

1. 등록된 라우터가 요청을 `health()`에 전달한다.
2. 데이터 조회 없이 본문 없는 응답을 반환한다.

## 데이터와 트랜잭션

사용하지 않음. DB·Aggregate 접근이나 데이터 변경이 없다.

## 조회와 인덱스

사용하지 않음. DB 조회와 목록 페이지네이션이 없다.

## 캐시

사용하지 않음. 핸들러는 요청마다 응답 객체를 생성하며 애플리케이션 캐시를 조회·저장하지 않는다.

## 구현과 검증

| 구분 | 위치 | 역할·확인하는 동작 |
| --- | --- | --- |
| 구현 | [health.py — health()](../../../src/mdm_demo/presentation/routers/health.py) | 요청 처리 |
| 조립 | [app.py — app.include_router()](../../../src/mdm_demo/app.py) | 라우터 등록 |
| 사용처 | [compose.yaml — services.api.healthcheck](../../../compose.yaml) | 컨테이너 생존 확인에 사용 |
| 검증 | [smoke.py — main()](../../../scripts/smoke.py) | 실제 HTTP 응답 상태 확인 |
| 검증 | [smoke.py — check_api_docs()](../../../scripts/smoke.py) | OpenAPI의 응답 정의 확인 |

- 검증 진입점: [Makefile](../../../Makefile)의 `make smoke`. 실행 전제는 [프로젝트 README](../../../README.md)를 따른다.
- 검증 공백: 전용 단위·API 테스트와 응답 본문이 비어 있는지 확인하는 검사는 없다. 스모크 검사의 DB·Redis 연결 확인은 별도 검사이며 이 엔드포인트의 동작이 아니다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [API 문서 제공](../api-documentation/api-reference.md) | 헬스 체크의 요청·응답 명세를 열람할 수 있음 |

[운영 목차](README.md)
