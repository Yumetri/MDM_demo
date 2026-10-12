# 이슈 #7 — Year 구현 계획

2026-10-12 사용자와 합의한 **구현 계획과 완료 기록**이다. 업무 규칙은 [Year](../features/dimension/year.md)·[YearLog](../features/dimension/year-log.md), HTTP 계약은 [API 규약](../api-conventions.md#yearyearlog-http-계약)에서 관리한다. 상세 명세를 티켓에 복제하지 않는다. 요구사항 협의 후 사용자 요청으로 구현·테스트·Scalar 검수를 수행했다. 결과는 [검증 보고](../reports/issue-7-validation.md)를 따른다.

## 기준과 통합

- 담당 기능: 제품 출시 연도 차원과 전용 이력 저장·조회, 이슈 #7.
- 기준: origin/main, 000b7e1a01e7c9e1c6c74e4026d1ab957d138556.
- 브랜치: codex/issue-7-year-dimension.
- 워크트리: /Users/tagit/.codex/worktrees/issue-7-year-dimension/MDM_demo.
- 선행 변경: 병합된 PR #15(차원별 공통 타입 분리), #16(차원별 UoW), #17(차원별 앱 조립). 추가 선행 PR은 현재 없다.
- 2026-10-12 원격 main을 fetch하고 열린 PR 목록을 확인했다. main 추가 변경·열린 PR은 없었다.
- 같은 저장소의 「6번 티켓 구현 계획 구체화」(Category), 「8번 티켓 구현 계획 구체화」(Network), 「티켓 9 구현 계획 구체화」(Memory)의 최근 대화를 읽었다. 모두 요구사항 협의 중이다. 메시지를 보내거나 작업을 위임하지 않았다.
- 세 작업의 worktree 상태도 읽었다. Category·Network는 현재 변경이 없고 Memory는 memory.md 추가·Dimension 목차 변경이 있었다. 관측 시점의 상태이며 이후 구현 범위는 다시 확인한다.
- 공통 충돌 가능 경로는 API 규약·오류 카탈로그·기능 등록 목록·fixture 목록·기능 목차·README·마이그레이션 metadata 등록이다. Year는 자기 항목만 최소 추가하고 다른 작업의 요구사항을 대신 변경하지 않는다.
- 공통 구조 선행 변경은 이미 main에 병합되었다. 독립 기능 PR 사이의 추가 의존성은 만들지 않는다. 신규 마이그레이션 ID는 기능별로 다르게 두고 먼저 병합된 기준을 반영한 뒤, 다중 head가 발생하면 기존 리비전을 다시 쓰지 않고 필요한 merge revision을 검토한다.
- 착수 기준 Alembic 단일 head는 0005_merge_brand_country였다. 구현한 고유 ID 0006_year_dimension이 현재 단일 head이며 기존 리비전은 보존했다.
- 최종 검증·리뷰 전에 원격 기준을 다시 확인·반영한다. 패치가 바뀌면 검증과 두 리뷰를 다시 수행한다.

## 확인한 기존 구현

- [Model 도메인](../../src/mdm_demo/domain/entities/model.py), [유스케이스](../../src/mdm_demo/application/use_cases/model.py): 도메인 변경·같은 값 수정 생략·같은 UoW에 변경/로그 저장.
- [공통 UoW](../../src/mdm_demo/infrastructure/persistence/unit_of_work.py), [Model UoW](../../src/mdm_demo/application/ports/units_of_work/model.py): 저장소별 Protocol, 한 세션, commit·rollback·취소 정리.
- [조립](../../src/mdm_demo/composition/model.py), [명시적 기능 목록](../../src/mdm_demo/composition/registry.py), [fixture](../../tests/fixtures/model.py): 기능별 자원 조립·테스트.
- [OpenAPI 원본](../../src/mdm_demo/presentation/schemas/model_examples.py), [예제 복원](../../src/mdm_demo/presentation/openapi.py), [실행 테스트](../../tests/api/test_model_openapi_examples.py): 실제 요청 위치의 이름 있는 예제, null 보존, 기본 cursor 생략.
- [기능맵](../features/README.md), [차원 목차](../features/dimension/README.md), [템플릿](../templates/feature.md), [API 규약](../api-conventions.md)을 확인했다.
- 워크트리 소스를 사용해 실제 app.openapi()를 생성했다. 4개 차원 CRUD·로그 경로와 실행 예제가 있으며 선택적 cursor에는 고정 예제/기본 토큰이 없다. 이번 조사에서는 브라우저 요청이나 기존 전체 테스트를 재실행하지 않았다.

## 확정한 공통 범위

- 합의 완료: Year·이력 목록 기본 20개·허용 1~100개, 이력 시각·로그 UUID 내림차순, 생성·수정의 YEAR_DUPLICATE/409 및 메시지, 검색·연도 범위 필터·총 개수 제외. 세부 계약은 API 규약에서 관리한다.
- UUID v4·UTC 생성/수정/기록 시각, 서버 발급 request ID, 기존 공통 성공·오류 envelope를 유지한다.
- 없는 Year·없는 로그 단건은 404, 기록 없는 대상 UUID의 이력 목록은 200 빈 목록.
- 인증·권한·행위자, 멱등성 키·자동 재시도, 캐시·자동 이력 만료는 이번 범위에서 제외한다.
- 변경 충돌은 행 잠금·DB UNIQUE로 처리하며 별도 낙관적 버전 검사는 추가하지 않는다.
- 중복 연도 전용 오류는 합의한 API 규약의 YEAR_DUPLICATE/409를 적용한다. 직접 코드 입력을 유도하는 기존 자동 코드 중복 메시지는 Year에 사용하지 않는다.
- 이 계획은 확정했다. 구현 착수·리팩터링·커밋·푸시는 각각 해당 요청·승인 범위를 따른다.

## 구현 순서

1. 구현 착수 요청 시 기준 main·동시 진행 작업·리비전 ID·실행 자원 사용 상태를 다시 확인한다. 업무 규칙·HTTP 계약은 이미 합의한 명세를 따른다.
2. Year 값 VO, 파생 코드, Entity·YearLog·차원별 오류·DTO·Repository/UoW/cursor 포트를 구현한다. int 검사에는 bool이 정수로 통과하지 않도록 정확한 타입 검증을 둔다.
3. ORM·Mapper·Repository·Year UoW·마이그레이션을 추가한다. year는 DB 정수, code는 문자열이며 DB에 UNIQUE(year), UNIQUE(code), 범위·일치 CHECK를 둔다. year_logs에 JSONB·NULL 조합 CHECK·변경 방지 트리거를 둔다.
4. 생성·수정·삭제·단건·목록·이력 유스케이스를 구현한다. 수정 시 두 값은 도메인 메서드에서 함께 바꾸며 스냅샷을 만들고 같은 트랜잭션으로 저장한다.
5. Year 목록용 서명 cursor를 별도 구현한다. 경계는 유일한 정수 year이고 다음 조건은 year < boundary.year, ORDER BY year DESC, LIMIT limit + 1이다. 생성 시각용 기존 Model cursor를 연도 cursor로 사용하지 않는다.
6. 이력은 대상 UUID·기록 시각·로그 UUID 경계를 사용하고 Year 전용 타입/서명 문맥으로 분리한다. 정렬은 occurred_at DESC/id DESC이며 다음 조건은 (occurred_at, id) < (boundary.occurred_at, boundary.id)다. 공유 코드 추출 리팩터링을 섞지 않는다.
7. Year 요청·응답·라우터·의존성·조립·예제·fixture를 추가하고 최소 등록 변경을 한다.
8. 기능별 단위·통합·API·예제 테스트와 전체 앱 회귀를 수행한다. 브라우저에서 Scalar 예제를 선택해 실제 요청을 실행한다.
9. 구현된 범위에 맞춰 README·API 규약·기능 문서·목차·검증 근거를 갱신한다.
10. 최신 기준 반영·검증 후 기준 커밋과 전체 패치 식별자를 기록하고 패치를 고정한다. security-diff-scan과 review-agent를 설치된 전체 절차대로 수행한다.
11. 결함 후보가 있으면 동일 패치·증거·요구사항을 두 별도 읽기 전용 서브에이전트에 주어 병렬 재검토한다. 두 의견·영향·수정안·검증 계획을 보고하고 사용자와 수정 범위를 합의한 뒤에만 수정한다. 최종 패치에서 검사·두 리뷰를 다시 수행한다.
12. 리뷰·검증 결과와 패치 일치를 보고하고 커밋·푸시는 별도 사전 승인을 따른다.

## 구현 파일과 공통 변경 범위

| 위치 | 예정 변경·이유 |
| --- | --- |
| domain/entities/year.py, year_log.py; domain/value_objects/year_value.py, year_code.py; domain/errors/year.py | 출시 연도 불변식·파생 코드·전후 스냅샷 |
| application/dto/year.py, year_log.py; application/errors/year.py | 정수 연도 DTO·차원별 중복 오류 |
| application/ports/repositories/year_repository.py, year_log_repository.py; application/ports/units_of_work/year.py; application/ports/cursors/year.py | 필요한 저장소만 사용하는 UoW·Year 경계 타입 |
| application/use_cases/year.py, year_log.py | 트랜잭션과 조회 |
| infrastructure/persistence/models/year.py, year_log.py; mappers/year_mapper.py, year_log_mapper.py; repositories/year_repository.py, year_log_repository.py; units_of_work/year.py | SQLAlchemy 구현·손실 없는 타입 변환·중복 변환 |
| infrastructure/pagination/year_cursor.py, year_log_cursor.py | 정수 연도 내림차순/기록 시각·UUID 내림차순의 별도 서명 문맥 |
| presentation/routers/year.py, year_log.py; schemas/year.py, year_log.py, year_examples.py; dependencies/year.py; composition/year.py | HTTP·실행 예제·기능 조립 |
| composition/registry.py | Year만 명시적으로 추가 |
| migrations/env.py, migrations/versions/0006_year_dimension.py | Year ORM metadata 등록·고유 리비전 |
| presentation/error_catalog.py | 합의한 Year 중복 오류 한 항목 추가 |
| presentation/schemas/examples.py | 문서 상단 공통 테스트 순서에 Year 준비 사항 연결·승인된 YEAR_DUPLICATE의 body.year 예제 매핑. 전체 순서 반복 금지 |
| tests/fixtures/year.py, tests/conftest.py | Year fixture와 플러그인 목록 추가 |
| tests/integration/persistence/test_dimension_merge_migration.py | 최신 단일 head를 Year 리비전으로 갱신하고 기존 merge 부모 관계·분기별 데이터/이력 보존 검증 유지 |
| tests/api/test_feature_composition.py | 현재 모든 차원에 name/code를 보내므로 Year에는 year를 보내도록 필요한 입력 분기만 추가 |
| tests/unit/domain/, tests/unit/application/, tests/integration/persistence/, tests/api/ | Year·YearLog 동작/마이그레이션/예제 검사 추가 |
| README.md, docs/api-conventions.md, docs/features/api-documentation/api-reference.md, docs/features/dimension/README.md, year.md, year-log.md | 실제 구현 범위·HTTP 계약·목차·검증 근거 갱신 |

표의 domain/·application/·infrastructure/·presentation/·composition/ 경로는 src/mdm_demo/ 기준이며 migrations/·tests/·docs/·README.md는 저장소 루트 기준이다. 파일별 구현 링크는 기능 문서에 기록했다. 기존 차원의 Entity·VO·DTO·UoW·cursor·예제는 변경하지 않는다. 목록 등록 및 전체 앱 테스트의 필요한 변경만 포함하며 별도 공통 리팩터링이 필요해지면 범위를 먼저 설명하고 승인을 받는다.

## 검증 계획

| 종류 | 확인할 동작 |
| --- | --- |
| 도메인 | 1900/2999 성공, 1899/3000 실패, bool·float·str·None 거부, 자동 코드·동시 값 변경·UUID 유지·같은 값 수정 |
| 로그/Mapper | 정수 year와 문자열 code의 타입 보존, before/after 조합, 스냅샷 복사·불변성, 양방향 Mapper 왕복 |
| 유스케이스 | 중복 생성·중복 수정의 동일 오류, no-op 저장/commit 생략, Year·로그의 원자성 |
| PostgreSQL | UNIQUE·범위/일치 CHECK, 동시 같은 연도 생성, 서로 다른 행을 같은 연도로 수정, 행 잠금 수정/삭제, 로그 실패·commit 실패·취소 정리, 로그 UPDATE/DELETE 거부 |
| 마이그레이션 | 빈 DB·현재 head에서 업그레이드, 기존 4개 차원 데이터/로그 보존, ORM 일치·단일 head, Year 전용 다운그레이드/재적용 |
| 목록/cursor | 연도 내림차순·이력 시각/UUID 내림차순·실제 다음 페이지, limit 경계, 경계 행 삭제, 정수 경계의 엄격한 검증, 잘못된·빈·변조·다른 차원·다른 목록·다른 UUID 토큰 거부 |
| API | 필수/불필요 필드·입력 타입·범위, CRUD 상태·코드/UUID 변경 정책, 같은 값 수정, 삭제 후 404·이력 보존·재등록 분리 |
| OpenAPI/Scalar | 이름 있는 정상/실패/경계 예제의 실제 실행, null 보존·응답 스키마 타입, 204 본문 없음, 실제 UUID·cursor 복사, 첫 페이지 생성 코드와 실제 요청에서 cursor 생략 |
| 전체 앱 | Year 격리 조립과 5개 차원 전체 조립, 오류·UoW·cursor 교차 사용 방지, 계층 경계·라우트/상태 등록·자원 수명 회귀 |

- 진입점: make check 또는 make check-container, make test-container, make compose-check, make up, make smoke. 원시 검사 명령은 Makefile에서만 관리하며 uv run --locked를 따른다.
- 실행 자원은 착수 시 작업별 Compose 프로젝트명·이미지 태그·API/DB 호스트 포트·DB/볼륨을 격리한다. 현재 compose.yaml의 고정 이미지 이름과 DB 포트는 프로젝트명만으로 격리되지 않으므로 임시 override를 사용하고 포트 사용 상태를 먼저 확인한다. 다른 작업의 컨테이너·볼륨을 종료/초기화하지 않는다.
- 마이그레이션 다운그레이드는 Year 데이터와 이력만 제거하며 기존 차원은 보존해야 한다. 공유한 기존 리비전을 다시 쓰지 않는다.
- 구현·전체 테스트·Scalar 검수를 수행했다. 완료 결과는 검증 보고에 기록하고 문서에는 git diff --check·상대 링크·규칙 간 일관성을 확인한다.


## Scalar 예제 결함 처리

초기 패치의 2024.0 예제를 Scalar가 2024로 전송하는 P2 문서 실행 결함을 확인했다. 같은 패치와 브라우저 증거를 두 읽기 전용 검토자에게 독립적으로 제공했고 두 의견이 일치했다. 사용자가 수정 범위를 승인한 뒤 실행 예제를 2024.5로 변경하고 생성·수정의 raw 2024.0 거부 및 데이터/로그 보존 테스트를 추가했다. API strict 정수 계약은 유지했다. Scalar 생성 코드·실제 본문·422·데이터/이력 보존을 재검증했다.

## 409 응답 예제 결함 처리

고정 패치 af9d89920ed541a8bd383b5ce44091b79d37128bd70de091c70414d1947938ad의 Year 중복 예제 details가 비어 있는 P2를 두 독립 읽기 전용 검토자가 확인했다. 사용자가 제안 범위를 승인한 뒤 공통 responses에 YEAR_DUPLICATE → body.year 매핑 2줄과 생성·수정 실제 error 객체/OpenAPI 예제 정확 비교 회귀 테스트만 추가했다. Scalar 실제 POST·PATCH 409 및 예제 일치와 전체 685개 테스트를 재검증했다. 런타임 API 계약은 유지했다.
