# 이슈 #7 — Year 구현·검증 보고

2026-10-12, codex/issue-7-year-dimension. 기준 main은 000b7e1a01e7c9e1c6c74e4026d1ab957d138556이다. [Year](../features/dimension/year.md)·[YearLog](../features/dimension/year-log.md)·[API 계약](../api-conventions.md#yearyearlog-http-계약)에 합의한 동작을 구현했다.

## 구현 결과

- 제품 출시 연도 1900~2999, JSON 정수만 허용하고 연도 자체를 유일하게 관리한다. 코드 직접 입력은 금지하며 서버가 연도 문자열을 생성한다.
- 연도 수정은 UUID를 유지하고 코드도 함께 바꾼다. 같은 값은 시각·데이터·이력을 변경하지 않는다. 생성·수정 중복은 YEAR_DUPLICATE/409다.
- 물리 삭제 후 이력을 보존하고 같은 연도 재등록은 새 UUID를 발급한다. 로그는 추가 전용이다.
- Year·YearLog를 같은 UoW/세션/트랜잭션으로 저장한다. 변경은 행 잠금, 중복은 DB UNIQUE, 연도 범위·코드 일치는 CHECK로 보장한다.
- Year 목록은 연도 내림차순, 이력은 기록 시각·로그 UUID 내림차순이다. 서명 cursor를 목록별·대상별로 구분한다.
- 전용 조립·오류·DTO·cursor·UoW·fixture와 고유 마이그레이션을 추가했다. 기존 차원 규칙은 변경하지 않았다.

## 자동 검증

| 검사 | 결과 |
| --- | --- |
| make format | Year 변경 파일 포맷 적용. 무관한 기존 구현 변경 없음 |
| make check | Ruff 린트·포맷, Pyrefly 경고 이상 0 |
| make test-unit | 288개 통과 |
| make test-container | 수정 후 전체 685개 통과, Alembic upgrade/check 통과 |
| make compose-check | 작업별 override 구성 통과 |
| make up / make smoke | 격리 API·PostgreSQL·Redis 정상, 문서·DB·Redis 연결 통과 |

PostgreSQL은 실제 컨테이너에서 검사했다. 빈 DB와 기존 head, 기존 Brand/Country 각 분기에서 최신 단일 head까지 업그레이드하고 기존 데이터·이력을 보존한다. Year 다운그레이드/재적용·ORM 일치도 확인했다. 동시 중복 생성·같은 연도로의 동시 수정·행 잠금 수정/삭제, 로그 저장 실패·commit 실패·취소와 세션 정리, Mapper 왕복·로그 UPDATE/DELETE 거부, 페이지 경계 삭제·cursor 문맥/변조·타입/범위를 검사했다.

기존 merge 검사는 0005를 최신 head로 고정했기 때문에 초기 전체 검사에서 4개가 실패했다. Year 이후 단일 head와 merge 부모 관계를 함께 검사하도록 갱신했으며 기준을 완화하지 않았다.

## 실제 Scalar 브라우저 검수

검수 주소는 http://127.0.0.1:8007/docs다. Playwright로 실제 브라우저에서 예제를 선택하고 Send를 눌러 생성된 요청 코드·실제 전송·응답을 확인했다.

| 시나리오 | 결과 |
| --- | --- |
| 문서 렌더링·Year 준비 안내·정수 범위·필수 필드 | 정상, 초기 CDN/문서 로딩 오류 없음 |
| 자동 코드 생성·1900/2999 경계 | 201, 응답 정수 year·문자열 code 일치 |
| 중복·null·문자열·boolean·직접 code·null 본문 | 각각 문서대로 409 또는 422 |
| 실제 UUID 단건·같은 값 수정·연도 수정 | 200, no-op의 시각 유지, 실제 변경의 UUID 유지·코드 동시 변경 |
| Year 첫 페이지·실제 cursor 다음 페이지 | 200 내림차순, 생성 코드와 실제 첫 요청 모두 cursor 생략 |
| 잘못된 cursor 수동 입력 | INVALID_CURSOR/400 |
| 삭제·재삭제 | 204 본문 없음, 재삭제 NOT_FOUND/404 |
| 삭제 후 이력 목록·실제 로그 UUID 단건 | 200 이력 보존, delete→update→create 내림차순, request ID 구분 |
| 이력 limit=1·실제 다음 cursor | 첫 delete 다음 update, 첫 요청 cursor 생략 |
| 수정된 실수 예제 POST/PATCH | 생성 코드·실제 본문 2024.5, 모두 422 |
| Raw 편집기로 2024.0 PATCH | 실제 본문 소수 표기 유지, 422 |
| 중복 생성·수정 409 오류 객체 | 실제 Scalar 전송 결과와 OpenAPI 예제의 code/message/details 정확히 일치 |
| 실패 후 데이터·이력 | 기존 데이터 동일, 생성 이력 한 건만 유지 |

실수 예제가 처음에는 JavaScript 직렬화 때문에 정수 2024로 전송됐다. 두 독립 검토가 같은 P2 결함으로 확인했고 사용자 승인 후 Year 예제·관련 테스트·설명만 수정했다. raw 2024.0 거부 계약은 그대로 유지했다. 최종 예제 선택과 Raw 본문을 모두 재검증했다. 의도적으로 실행한 400/404/409/422 요청의 브라우저 네트워크 오류 표시는 예상 실패이며 문서 번들 로딩 오류와 구분했다.

409 예제의 details가 실제 body.year 응답과 다른 P2 문서 결함도 두 독립 검토자가 확인했다. 사용자 승인 후 공통 예제 생성기에 Year 필드 매핑 2줄과 POST·PATCH 오류 객체 전체 비교 테스트를 추가했다. 런타임 계약은 유지했고 Scalar의 실제 중복 요청과 OpenAPI 예제 일치를 재검증했다.

## 실행 격리와 한계

Compose 프로젝트 mdm-year-7, 전용 이미지 mdm-year-7-api, API 8007·PostgreSQL 5437, 별도 DB/볼륨과 tmpfs 테스트 DB를 사용했다. 임시 override로 고정 이미지/DB 포트까지 분리했고 다른 작업의 컨테이너·DB·볼륨을 초기화하거나 종료하지 않았다.

인증·권한·행위자·캐시·검색·필터·총 개수·자동 이력 만료·자동 재시도는 합의한 범위 밖이다. 목록 순회 중 연도 수정/재등록의 항목 이동, 스냅샷 일관성과 실제 commit 순서는 보장하지 않는다. 대량 데이터 실행 계획·성능과 실제 네트워크 commit 응답 유실 복구는 검증하지 않았다.

검사 명령과 실행 전제는 [Makefile](../../Makefile)·[README](../../README.md), 계층별 파일과 수정 범위는 [작업 계획](../plans/issue-7-year-dimension.md)을 따른다. 최종 코드·보안 리뷰 결과는 별도 리뷰 산출물로 보고한다. 커밋·푸시는 수행하지 않았다.
