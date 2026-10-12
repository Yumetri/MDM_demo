# 이슈 #9 — Memory 구현 계획

2026-10-12 사용자와 전체 계획을 확정하고 구현·테스트·Scalar 검수를 요청받았다. 아래는 확정한 구현 계획이다. 커밋·푸시는 별도 승인 범위를 따른다.

상세 업무 규칙은 [Memory](../features/dimension/memory.md)·[MemoryLog](../features/dimension/memory-log.md), HTTP 필드·경로·오류·상태·페이지네이션은 [API 규약](../api-conventions.md#memorymemorylog-http-계약)에서 관리한다. 티켓에는 상세 명세를 복제하지 않는다.

## 기준·선행 변경·병렬 통합

- 담당: 저장공간 용량 차원 CRUD 및 전용 이력 저장·조회, 이슈 #9.
- 최초 기준: 000b7e1a01e7c9e1c6c74e4026d1ab957d138556. PR 생성 전 main에 병합된 Year(PR #19)를 반영해 origin/main c1f94f6d8f2738cf20a5d29b33b00ef0ed634bf0으로 갱신했다. 공통 등록·문서·테스트에서 Year와 Memory를 모두 보존했다. 이후 충돌 해결 요청에 따라 Category·Network가 병합된 main 57a0a4f를 다시 통합했다. 기존 적용 리비전을 보존하고 0009_merge_memory_dimensions로 0008 main head·0007 Memory head를 연결한다.
- 브랜치: codex/issue-9-memory-dimension.
- 워크트리: /Users/tagit/.codex/worktrees/issue-9-memory-dimension/MDM_demo.
- 선행 PR #15(차원별 타입), #16(차원별 UoW), #17(명시적 조립)은 기준에 포함되어 있다. 이 구조를 재사용하며 별도 공통 리팩터링을 전제하지 않는다.
- 6·7·8번 워크트리의 상태·예정 계획을 읽었다. 기능별 구현 파일과 registry·마이그레이션 metadata·오류 카탈로그·fixture·API 계약·기능 목차·전체 조립 검사에 실제 변경이 있다. 계획 문서의 과거 상태 표현보다 현재 git 상태를 기준으로 충돌 경로를 판단한다.
- 독립 기능 PR 사이에 추가 의존성을 만들지 않는다. 먼저 병합된 기능을 최신 main에서 반영하고 공통 등록 파일의 각 기능 항목을 보존한다. 구체 병합 순서는 PR 상태에 따라 결정하며 다른 작업에 메시지·변경·위임을 수행하지 않는다.
- 착수 당시 migration head는 0005_merge_brand_country였다. 고유 후보 revision 0006_memory, 파일 0006_memory_dimension.py를 사용하며 착수 시 실제 중복·head를 다시 확인한다.
- Year 통합 후 0007_merge_year_memory를 추가해 0006_year_dimension·0006_memory를 단일 head로 연결했다. 기존 적용 리비전을 보존하고 각 선행 head에서 데이터·로그 보존을 검증한다. 병렬 head 통합은 스키마 호환성을 확인하고 필요하면 별도 merge revision을 추가한다. 이미 공유·적용한 리비전의 ID·부모·내용을 바꾸지 않는다. 빈 DB와 각 선행 head에서 최종 head 업그레이드를 확인한다.
- 실행 자원 후보: Compose 프로젝트 mdm-memory-9, 이미지 mdm-memory-9-api, API 호스트 포트 18009·PostgreSQL 15439, 개발 DB mdm_memory. 임시 override로 migrate/api/test 이미지와 API·DB 포트를 모두 교체한다. 포트 사용 상태·렌더링한 Compose 설정을 실행 직전에 확인한다.
- 개발 볼륨은 프로젝트별로 분리한다. 테스트는 이 프로젝트의 별도 postgres-test와 mdm_test DB·tmpfs를 사용한다. 기존 안전 검사에 맞춰 테스트 DB 이름은 유지하되 서비스·실행 자원은 분리한다. 다른 작업의 컨테이너·볼륨을 종료·초기화하지 않는다.
- 최종 검증·리뷰 전 원격 main을 다시 확인·반영하고 패치가 달라지면 관련 검사와 두 필수 리뷰를 다시 수행한다.

## 확인한 기존 구현

- [Company 유스케이스](../../src/mdm_demo/application/use_cases/company.py)·[Repository](../../src/mdm_demo/infrastructure/persistence/repositories/company_repository.py): 도메인 메서드, 행 잠금, 변경·로그 동시 저장, 알려진 제약만 중복으로 변환.
- [차원 UoW](../../src/mdm_demo/application/ports/units_of_work/company.py)·[공통 SQLAlchemy UoW](../../src/mdm_demo/infrastructure/persistence/unit_of_work.py): 필요한 Repository Protocol, 같은 세션, 명시적 commit·rollback·취소 정리.
- [차원 조립](../../src/mdm_demo/composition/company.py)·[registry](../../src/mdm_demo/composition/registry.py)·[fixture 등록](../../tests/conftest.py): 기능별 조립·독립 테스트·전체 앱 검사.
- [Model 예제](../../src/mdm_demo/presentation/schemas/model_examples.py)·[예제 복원](../../src/mdm_demo/presentation/openapi.py)·[실행 테스트](../../tests/api/test_model_openapi_examples.py): 실제 본문·경로·쿼리 예제, null 보존, cursor 기본 입력 생략.
- 워크트리 소스에서 app.openapi()를 생성해 Company·Model·Brand·Country CRUD/로그 경로·성공/실패 예제와 cursor에 고정 예제가 없는 것을 확인했다. Memory는 기존 생성 스키마에 없다.
- 전체 기능맵·Dimension 목차·기능 템플릿·API 규약·README·AGENTS.md·Makefile을 확인했다. 이번 계획 단계에서는 기존 전체 테스트·실제 DB·브라우저 HTTP 요청을 재실행하지 않았다.

## 확정 구현 계획

| 순서 | 계층·작업 | 주요 설계·책임 |
| --- | --- | --- |
| 1 | 도메인 | 불변 MemorySize VO가 정수 범위·단위 정규화·코드/환산값 계산을 담당. Memory Entity가 변경과 UUID·시각 정책을 책임짐 |
| 2 | MemoryLog | id·capacity·unit·code 스냅샷 복사·불변화. 문자열과 정수 타입을 보존하고 작업별 전후 값 조합 검증 |
| 3 | Application | DTO·차원 오류·Repository·cursor·Memory UoW/로그 전용 UoW Protocol. 트랜잭션과 오류 변환은 유스케이스에 둠 |
| 4 | 영속성 | Memory·MemoryLog ORM·Mapper·Repository·차원 SQLAlchemy UoW. DB UNIQUE/CHECK·행 잠금·공통 UoW 재사용 |
| 5 | 마이그레이션 | memories/memory_logs, 인덱스·생성 컬럼·제약·추가 전용 로그 트리거 추가. 기존 리비전 보존 |
| 6 | HTTP·조립 | 기능별 schema/router/dependency/composition, 명시적 registry 등록. 기존 공통 응답·예외 처리·OpenAPI 복원 재사용 |
| 7 | 검증·문서 | 기능별·전체 앱 테스트, 실제 PostgreSQL·Scalar 예제 실행, README·기능 문서·규약·검증 근거 갱신 |
| 8 | 최종 리뷰 | 최신 main 반영 후 기준 커밋·전체 패치 식별자 고정, security-diff-scan 및 review-agent 절차 수행 |

MemorySize는 용량·단위를 함께 검증하는 값 객체다. 파생 코드만을 위해 불필요한 입력 VO·공통 추상 클래스를 만들지 않는다. 도메인은 FastAPI·SQLAlchemy를 import하지 않으며 Entity 필드는 유스케이스에서 직접 대입하지 않는다.

Memory와 로그 전용 스냅샷 타입에 정수 capacity를 포함한다. 기존 로그의 dict[str, str]를 그대로 복제하거나 기존 Company/Model 타입을 전역 확장하지 않는다. Mapper에서 숫자를 문자열로 바꾸지 않으며 왕복·스냅샷 독립성을 검증한다.

## DB·동시성·실패 처리

- memories: UUID PK, capacity는 INTEGER, unit은 GB/TB 문자열, code는 길이 12의 파생 문자열, created_at/updated_at은 UTC timestamptz.
- capacity_gb는 BIGINT 생성 컬럼. GB는 capacity의 큰 정수 변환값, TB는 큰 정수 변환 후 1000배로 계산한다. 곱셈 이전에 형변환해 INTEGER 중간 계산의 넘침을 막는다.
- UNIQUE(capacity_gb)·UNIQUE(code), 용량 범위·단위·code = capacity 문자열 + unit CHECK를 둔다. 내부 환산값을 임의 저장하지 않아 DB의 동치 중복 검사가 도메인 계산과 일치하게 한다.
- 수정·삭제 대상은 SELECT FOR UPDATE 후 읽는다. 별도 낙관적 버전·ETag를 도입하지 않고 같은 항목의 연속 수정은 나중 처리된 값이 최종 값이 된다.
- 다른 항목과의 용량 충돌은 DB UNIQUE로 보장한다. 동시 같은 용량 생성·빈 용량으로의 동시 변경에서도 한 요청만 성공하고 다른 요청은 계약 초안의 중복 오류를 반환하도록 검증한다.
- 알려진 용량·코드 UNIQUE 위반만 DuplicateMemoryCapacity/application 오류로 변환한다. 사용자 코드를 받을 수 없으므로 기존 직접 코드 입력 안내 오류는 재사용하지 않는다.
- no-op은 저장·commit·로그를 생략한다. 표기 변경은 용량·단위·코드와 시각을 함께 저장하고 update 로그를 기록한다.
- Memory 변경과 로그 추가는 같은 세션·UoW다. 로그 flush 실패·commit 실패·예외·취소 시 공통 UoW의 rollback·정리가 실행되는지 검증한다.
- 로그 원본 UUID는 FK 없이 보존한다. JSONB 전후 값의 NULL 조합 CHECK와 UPDATE/DELETE 거부 트리거를 추가한다. 수정·삭제 API나 자동 이력 만료·행위자·자동 재시도·멱등성 키는 추가하지 않는 제안이다.

## 목록·cursor·이력 계획

- Memory는 합의한 생성 시각·UUID 오름차순 경계, 로그는 기록 시각·UUID 오름차순 경계를 사용한다.
- 기능별 boundary 타입과 HMAC 서명 문맥을 분리한다. 로그 cursor는 대상 Memory UUID까지 묶는다. 다른 차원·다른 목록·다른 대상의 cursor를 거부한다.
- limit + 1 조회로 다음 페이지를 판정한다. 경계 행 삭제 후에도 cursor의 경계값으로 조회하며 총 개수·스냅샷 일관성·commit 순서는 제공하지 않는다.
- 로그 메타데이터는 기존 차원처럼 로그 UUID·Memory UUID·작업·UTC 기록 시각·변경 당시 서버 request ID를 사용하는 제안이다. 현재 조회 요청 ID와 변경 당시 요청 ID를 구분한다.
- 로그 목록은 현재 Memory 존재를 검사하지 않고 기록을 조회하며 기록 없는 UUID는 빈 목록이다. 로그 단건은 PK로 조회한다.

## 파일·공통 변경 범위

아래 src 경로는 src/mdm_demo/ 기준이다. 구현 파일·검증 근거는 기능 문서에서 연결한다.

| 위치 | 범위·이유 |
| --- | --- |
| domain/entities/memory.py, memory_log.py; value_objects/memory_size.py; errors/memory.py | 저장공간 불변식·파생 코드·수정·스냅샷 |
| application/dto/memory.py, memory_log.py; errors/memory.py | 숫자 타입을 보존하는 DTO·중복 오류 |
| application/ports/repositories/memory_repository.py, memory_log_repository.py; units_of_work/memory.py; cursors/memory.py | Memory와 로그 전용 저장소·UoW·cursor 타입 |
| application/use_cases/memory.py, memory_log.py | 트랜잭션·조회·도메인/DB 오류 변환 |
| infrastructure/persistence/models/memory.py, memory_log.py; mappers/memory_mapper.py, memory_log_mapper.py; repositories/memory_repository.py, memory_log_repository.py; units_of_work/memory.py | ORM·Mapper·잠금·제약 위반 분류·같은 세션 조립 |
| infrastructure/pagination/memory_cursor.py, memory_log_cursor.py | 기능별 서명 cursor |
| presentation/schemas/memory.py, memory_log.py, memory_examples.py; routers/memory.py, memory_log.py; dependencies/memory.py; composition/memory.py | 엄격한 요청·자동 코드 응답·실행 예제·명시적 조립 |
| composition/registry.py | Memory 모듈만 최소 추가 |
| migrations/env.py, migrations/versions/0006_memory_dimension.py | Memory ORM metadata 등록·고유 신규 revision |
| presentation/error_catalog.py | 저장공간 용량 중복 오류 한 항목 추가 |
| presentation/schemas/examples.py | 공통 Introduction에서 Memory 준비 순서만 연결, 각 API에 공통 안내 반복 금지 |
| tests/fixtures/memory.py, tests/conftest.py | Memory fixture·등록 목록 추가 |
| tests/api/test_feature_composition.py | memories 경로와 capacity/unit 생성 입력 분기. 기존 name/code 입력을 Memory에 보내지 않게 변경 |
| tests/integration/persistence/test_dimension_merge_migration.py 및 필요한 마이그레이션 검사 | Brand/Country의 기존 병합 노드는 유지하고 Memory 추가 이후 최신 단일 head·보존을 검증. 불필요한 공통 테스트 재작성 금지 |
| tests/unit/domain/test_memory.py; tests/unit/application/test_memory.py, test_memory_log.py, test_memory_cursor.py | 불변식·정수 타입·유스케이스·서명 경계 |
| tests/integration/persistence/test_memory.py, test_memory_migration.py | Mapper·동시성·원자성·DB 제약·마이그레이션 |
| tests/api/test_memory.py, test_memory_log.py, test_memory_openapi_examples.py | 계약·실행 예제·로그 조회 |
| README.md, docs/api-conventions.md, docs/features/dimension/README.md, memory.md, memory-log.md, docs/features/api-documentation/api-reference.md | 실제 구현 범위·명세·목차·검증 근거 갱신 |

기존 Company·Model·Brand·Country의 Entity·VO·유스케이스·cursor·UoW를 바꾸지 않는다. 공통 파일에서는 Memory에 필요한 등록·계약·검증만 수정한다. 공통 구조 변경이 필요해지면 별도 리팩터링 범위·허가로 처리한다.

## 검증 계획

| 종류 | 주요 확인 항목 |
| --- | --- |
| 도메인 | 1/상한 성공, 0/음수/상한+1 실패, bool·float·str·null 거부, 단위 trim/대문자/내부 공백/비허용 단위, 자동 코드·환산값 |
| 수정 | UUID·생성 시각 유지, 코드 재생성, 동일 값 저장·commit·시각·로그 생략, 1TB→1000GB 표기 변경의 이력 |
| 로그/Mapper | 숫자 capacity·문자열 unit/code 보존, before/after 조합, 복사·불변성·Mapper 왕복 |
| PostgreSQL | 동치 용량·코드 UNIQUE, 범위/단위/파생 코드 CHECK, 환산 생성 컬럼과 최대 TB 변환, 로그 UPDATE/DELETE 거부 |
| 원자성·동시성 | 중복 생성/수정, 동시 같은 환산 용량 생성·수정의 단일 성공, 같은 항목 수정/삭제 행 잠금, 로그 실패·commit 실패·취소·미커밋 정리 |
| 마이그레이션 | 빈 DB·현재 head·필요한 병렬 선행 head 업그레이드, 기존 데이터·로그 보존, ORM 일치·최종 단일 head, Memory 전용 downgrade/재적용 |
| API | 필수·허용 필드/입력 타입/범위, 없는 대상·재삭제, 같은 값·표기 변경·중복 수정, 삭제 후 이력·재등록 UUID 분리 |
| cursor | limit 1/20/100·0/101, 다음 페이지·경계 삭제, 잘못된/빈/변조/다른 차원/목록/대상 토큰, limit 변경 |
| OpenAPI | 본문·경로·query 예제와 예상 상태/오류/사전 조건, 실제 스키마의 null·정수 타입, 정상 cursor는 응답에서 복사, 204 본문 없음 |
| Scalar | 새 UI에서 예제 선택·실제 생성/수정/삭제/로그·중복·경계값 실행, UUID 복사·다음 페이지, 생성 요청 코드와 실제 전송 모두 첫 페이지 cursor 생략 |
| 전체 앱 | Memory 격리 조립과 전체 기능 조립, 기능 간 cursor/오류/UoW 분리, 계층 의존성·라우트 중복·자원 수명 회귀 |

실행 진입점은 [Makefile](../../Makefile)의 make check 또는 make check-container, make test-container, make compose-check, make up, make smoke다. 검증은 uv run --locked를 사용하고 원시 검사 명령을 문서·CI에 복제하지 않는다. 필요한 검사 진입점만 Makefile에 추가한다.

## 리뷰·현재 검증 범위

- Memory와 MemoryLog를 구현하고 정적 검사·Memory 구현 당시 단위 315개·Year 통합 후 실제 PostgreSQL 전체 1160개·마이그레이션/ORM 일치·Scalar 요청을 검증했다. 문서 공백·링크·규칙 일관성도 확인한다. 실수 실패 예제의 Scalar 직렬화 P2는 두 독립 검토자가 확인했고, 2026-10-12 사용자가 승인한 범위로 수정했다. POST·PATCH 예제는 256.5를 사용하며 원시 JSON 256.0의 422·데이터/이력 불변 테스트 2개와 실행 안내를 추가했다. 실제 Scalar에서도 두 예제의 256.5 전송·422·원본/시각/이력 불변을 재확인했다.
- README의 Memory 구현 범위·마이그레이션·로그 보존 설명을 갱신했다. 상세 규칙은 기능 문서·API 규약을 참조한다.
- Year 통합에 따른 기존 Year 마이그레이션 검사는 해당 리비전의 roundtrip을 유지하고 최종 head 확인만 갱신했다. 공통 이전 merge 검사도 해당 노드의 roundtrip을 유지한다. 별도 Year·Memory merge 검사에서 두 선행 head 각각/동시 적용 상태와 기존 로그 보존·merge-only downgrade/재적용을 검증한다.
- 통합 앱의 make up·make smoke를 통과했고 새 Scalar에서 Year·Memory 안내가 함께 표시됨을 확인했다. Memory 첫 페이지의 생성 코드·실제 요청은 cursor를 생략하고 200을 반환한다.
- 커밋 전 최종 기준 커밋·패치 식별자와 전체 대상을 기록하고 수정하지 않은 패치에 security-diff-scan 및 review-agent의 설치된 전체 절차를 수행한다.
- 결함 후보가 나오면 같은 패치·증거·요구사항을 별도 읽기 전용 서브에이전트 2개에 주고 병렬 재검토한다. 실재성·조건·영향·반례·수정안·검증 계획과 두 의견의 일치/불일치를 보고하고 수정 방향·범위를 합의한 뒤에만 수정한다.
- 수정 후 필요한 검사·두 리뷰를 최종 패치에서 다시 수행한다. 미수정 문제 수용 시 잔여 위험·결정을 기록하고 해당 상태의 커밋 승인을 받는다.
- 리팩터링·커밋·푸시를 수행하지 않았다. 리뷰 완료는 이들 행위의 사전 허가를 대신하지 않는다.


## main 충돌 해결 재검증

- 2026-10-12 main 57a0a4f2e4a072fd5ea55208d473475cf9e5dc01(Category PR #20·Network PR #22)을 병합한다. 기존 Memory 커밋 fd67db6을 첫 부모로 보존한다.
- 8개 차원의 등록·오류·본문 안내·fixture·API 계약·목차를 함께 유지한다. 기존 적용 리비전을 바꾸지 않고 0009_merge_memory_dimensions에서 main의 0008 head와 Memory의 0007 head를 연결한다.
- 빈 DB·개별 0006/0007/0008 리비전·양쪽 head 동시 적용 등 10개 상태에서 8개 차원의 데이터·이력 보존, merge-only downgrade·재적용을 검증했다. 기존 하위 merge 검사는 해당 리비전의 roundtrip을 유지하고 최신 head 확인만 갱신한다.
- 첫 실행은 새 테스트의 downgrade 기대값이 이전 부모였던 10개 경우에서 실패했다. 실제 부모로 수정한 뒤 전체 1160개가 통과했다. Ruff·Pyrefly와 make up·make smoke도 통과했다. 새 Scalar에서 모든 차원과 안내가 표시되고 Memory 목록의 실제 요청이 cursor 없이 200을 반환한다.
- 병합 커밋 전체 변경을 첫 부모 fd67db6 기준으로 고정해 두 필수 리뷰를 수행한다. PR #21의 main 대상은 유지한다.
