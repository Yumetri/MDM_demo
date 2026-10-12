# 이슈 #8 Network 구현 계획

2026-10-12 기준. 사용자와 업무 규칙·공통 HTTP·이력 정책을 합의하고 전체 계획을 확정했다. 이 계획에 따라 Network·NetworkLog를 구현했고 아래에 실제 검수 결과를 기록한다.

## 기준과 확인한 기존 작업

- 티켓: [#8](https://github.com/Yumetri/MDM_demo/issues/8), 상위 원칙: [#1](https://github.com/Yumetri/MDM_demo/issues/1).
- 브랜치: `codex/issue-8-network-dimension`. 워크트리: `/Users/tagit/.codex/worktrees/issue-8-network-dimension/MDM_demo`.
- 기준: `origin/main`의 `000b7e1a01e7c9e1c6c74e4026d1ab957d138556`. 최신 fetch 후 HEAD와 일치한다.
- Company·Model·Brand·Country의 도메인·유스케이스·Repository·차원 UoW·조립·라우터·예제·검증과 [기능맵](../features/README.md)을 확인했다.
- 선행 공통 변경은 이미 main에 병합된 [PR #15](https://github.com/Yumetri/MDM_demo/pull/15) 공통 타입, [PR #16](https://github.com/Yumetri/MDM_demo/pull/16) 차원 UoW, [PR #17](https://github.com/Yumetri/MDM_demo/pull/17) 기능 조립이다. Network는 해당 구조를 사용하며 별도 공통 구조 변경을 전제하지 않는다.
- 기준 코드의 앱에서 OpenAPI를 생성해 Company·Model·Brand·Country와 각 로그의 7개 작업, 본문·경로·limit 예제, 첫 페이지 cursor 기본 생략을 확인했다. 기존 Network 경로는 없다. 이 확인은 실제 Scalar 요청 실행 검증을 대신하지 않는다.
- 기존 코드 정책을 복제하지 않는다. Network는 이름 정규화·유일성, 코드 1~20자·전체 추출, 두 목록 내림차순을 별도로 구현한다.

## 합의한 요구사항

- 의미·필드·입력·코드·수정·삭제·동시성·초기 데이터: [Network](../features/dimension/network.md).
- 스냅샷·원자성·조회·보존: [NetworkLog](../features/dimension/network-log.md).
- HTTP 계약은 [API 규약의 확정 명세](../api-conventions.md#networknetworklog-http-계약)에서만 관리한다. 업무 규칙·공통 정책·HTTP 표현을 구현·OpenAPI·검사에 반영했다.
- 인증·권한·캐시·검색·필터·선택 정렬·총 개수·초기 데이터 삽입은 제외하기로 합의했다. 별도 버전 검사도 없다.

## 합의한 공통 정책

- UUID v4·UTC, 서버 발급 request ID, 기존 성공·오류 envelope와 HTTP 상태를 유지한다.
- 문자열 타입 엄격 검증·알 수 없는 JSON 필드 거부. code 생략만 자동 생성이며 null·빈 값·공백만 있는 값은 거부한다. PATCH는 name 필수이며 code 입력을 거부한다.
- NUL·단독 surrogate는 기존 차원처럼 입력 오류다. 대문자 변환 후 길이를 검사한다. 정상 한글·이모지와 내부 공백은 보존한다.
- 이름·직접 코드 중복은 Network 전용 오류, 자동 코드 중복·생성 불가는 기존 공통 오류를 사용한다. 구체 코드·메시지는 API 규약을 따른다.
- 로그는 추가 전용이며 DB UPDATE/DELETE도 방지하고 자동 만료하지 않는다. 행위자·로그 직접 변경 API·통합 검색은 추가하지 않는다.
- cursor는 서명·목록 종류·정렬에 묶고 로그는 Network UUID에도 묶는다. 경계 삭제·동일 시각을 처리하되 총 개수·스냅샷 일관성은 보장하지 않는다.
- 멱등성 키·commit 응답 유실 복구·자동 재시도는 이번 범위에 추가하지 않는다.

## 구현 순서와 파일 범위

아래 Python 경로는 `src/mdm_demo/` 기준이며 나머지는 저장소 루트 기준이다. 계획한 파일 경로를 코드 표기로 유지하고 기능 문서에는 실제 구현·검사 링크를 연결했다.

| 순서 | 전용 경로·심벌 계획 | 작업 |
| --- | --- | --- |
| 1 | `domain/entities/network.py`, `network_log.py`, `domain/value_objects/network_name.py`, `network_code.py`, `domain/errors/network.py` | Entity 식별자 동등성, 불변 VO, 이름 정규화·길이·코드 전체 추출, rename/no-op·스냅샷 |
| 2 | `application/dto/network.py`, `network_log.py`, `application/errors/network.py`, `application/ports/repositories/network_repository.py`, `network_log_repository.py` | 입출력·오류·Repository 인터페이스 |
| 3 | `application/ports/cursors/network.py`, `application/ports/units_of_work/network.py`, `application/use_cases/network.py`, `network_log.py` | 차원 UoW·로그 전용 Protocol, 원자적 CRUD·로그 조회·오류 변환 |
| 4 | `infrastructure/persistence/models/network.py`, `network_log.py`, `mappers/network_mapper.py`, `network_log_mapper.py`, `repositories/network_repository.py`, `network_log_repository.py`, `units_of_work/network.py` | ORM·손실 없는 Mapper·DB 제약·행 잠금·공통 UoW 재사용 |
| 5 | `infrastructure/pagination/network_cursor.py`, `network_log_cursor.py` | 최신순 조회 식별자·서명 cursor. `.desc()` 정렬과 tuple `<` 경계를 함께 적용 |
| 6 | `migrations/versions/0006_network_dimension.py` | 고유 revision `0006_network`, 현재 parent `0005_merge_brand_country`. 테이블·제약·인덱스·로그 보호 트리거 |
| 7 | `presentation/dependencies/network.py`, `routers/network.py`, `network_log.py`, `schemas/network.py`, `network_log.py`, `network_examples.py` | 합의한 계약·응답·이름 있는 실행 예제 |
| 8 | `composition/network.py`, `tests/fixtures/network.py`, Network 전용 단위·통합·API 테스트 | 조립·격리 fixture·동작·회귀 검증 |
| 9 | 기능 문서·API 규약·README | 구현된 범위·근거·실제 검사 결과 갱신 |

공통 파일 수정은 아래 등록·계약에 한정한다. 필요한 공통 구조 리팩터링은 별도 범위·사전 합의로 다룬다.

- `composition/registry.py`: Network 모듈 한 개 등록.
- `migrations/env.py`: Network·NetworkLog ORM 명시적 등록.
- `presentation/error_catalog.py`: Network 이름·직접 코드 중복과 자동 생성 메시지 매핑만 추가.
- `tests/conftest.py`: Network fixture 등록. 기존 차원의 서비스 인자를 늘리지 않는다.
- `tests/api/test_feature_composition.py` 및 필요한 공통 검증: 전체 앱에 Network가 포함되고 격리 앱·라우트·UoW 계약을 유지하는지 검사.
- `docs/features/dimension/README.md`, `docs/api-conventions.md`, `README.md`: 링크·Network 계약·구현 범위만 추가. 전체 기능맵은 기존 Dimension 링크로 연결되어 별도 구조 변경이 필요 없다.
- 공통 WORKFLOW 안내는 기존 흐름을 재사용하고 Network 때문에 사실과 달라지는 안내가 있으면 해당 부분만 갱신한다.

## 병렬 통합과 실행 환경

- 2026-10-12 확인 시 열린 PR은 없다. Category(#6)는 명세·계획 정리 중, Year(#7)는 명세 문서 변경, Memory(#9)는 요구사항 협의·기능 문서 변경 중이다. 각 워크트리 상태·최근 대화에서 확인한 범위이며 이후 구현 범위와 순서는 다시 확인한다.
- 현재 겹치는 문서 경로는 Dimension 목차와 API 규약이다. 구현 시 registry·ORM 등록·오류 카탈로그·fixture·전체 앱 검사·README·마이그레이션 head도 겹칠 수 있다. 다른 작업에 직접 변경하거나 메시지를 보내지는 않았다.
- Network는 기존 main을 선행 기준으로 독립 개발한다. #6·#7·#9 사이에 기능 의존성은 만들지 않는다. 먼저 병합된 변경을 후속 작업에서 반영하고 공통 목록에서는 각 기능 항목을 보존한다. 실제 병합 순서는 PR 상태가 생긴 뒤 정한다.
- 착수 시 단일 migration head는 `0005_merge_brand_country`였으며 Network 추가 후 현재 head는 `0006_network`다. 이후 다른 기능이 먼저 병합되면 최신 head를 확인한다. 이미 공유·적용한 리비전의 ID·부모를 바꾸지 않고 호환성 검토 후 필요 시 merge revision을 추가한다.
- 실행 전용 Compose override로 프로젝트 `mdm-network-8`, 이미지 `mdm-network-8-api`, API 18008·PostgreSQL 15438을 제안한다. 사용 여부를 확인하고 비어 있는 포트를 선택한다. DB·사용자·개발 볼륨도 전용으로 분리하며 테스트는 이 프로젝트의 `mdm_test` DB와 별도 tmpfs 서비스를 사용한다.
- worktree만으로 실행 자원이 격리되지 않는다. 기본 image·고정 PostgreSQL 호스트 포트를 override하고 다른 프로젝트의 서비스·볼륨을 종료·초기화하지 않는다. override 작성 후 `make compose-check`로 확인한다.
- 최종 리뷰 직전 origin/main 재확인·반영 후 전체 앱 검증과 최종 패치 고정을 수행한다.

## 검증 계획

1. 도메인: trim/upper/NFC·대소문자·정준 동등 이름, 정규화 후 길이·대문자 확장 경계, 내부 공백·한글·기호·NUL/surrogate, 코드 1/20/0/21자·비ASCII·자동 전체 추출·공백/기호 제거·추출 없음, 불변 코드·Entity 동등성·no-op·로그 스냅샷.
2. 실제 PostgreSQL: Mapper 왕복, 이름·코드 DB 제약, 동시 생성·서로 다른 행의 같은 이름 수정, 행 잠금·수정/삭제 직렬화, 로그 저장 실패·commit 실패·취소 rollback/정리, 추가 전용 로그·삭제 후 보존·새 UUID 분리.
3. 최신순 cursor: Network·로그의 DESC/DESC와 `<` 경계, 동일 시각 UUID tie-break, 빈/마지막 페이지·limit 경계·경계 행 삭제, 잘못된 서명·조회 종류·정렬·타 대상 로그 cursor, 순회 중 생성/삭제의 일관성 한계.
4. 마이그레이션: 빈 DB·현재 head에서 업그레이드, 기존 네 차원 데이터·이력 보존, Network upgrade/downgrade·재적용과 ORM 일치·단일 head. 병렬 heads가 존재하면 각 선행 head·병합 경로도 검증한다.
5. API·OpenAPI: CRUD·코드 생략/명시 null/빈값·중복·없는 대상·no-op·삭제 후 조회·이력·cursor 오류·서버 request ID·정상/오류 envelope. 예제 스냅샷과 null 보존·204 본문 없음. 예제를 스키마에서 꺼내 실제 요청으로 실행한다.
6. Scalar: 새 UI에서 기본 정상 요청, 예제 선택·생성/수정/삭제·이력·중복·동적 UUID 복사·실제 cursor 다음 페이지 실행. 첫 페이지의 생성 코드와 실제 HTTP 요청 모두에서 cursor 생략 확인. 공통 테스트 순서는 Introduction에 한 번만 둔다.
7. 전체 회귀·통합: 기존 Company·Model·Brand·Country 및 전체 앱 조립·계층 의존성·중복 경로·fixture 격리·UoW 수명 검사.

기존 [Makefile](../../Makefile) 진입점으로 `make check-container`(또는 `make check`), `make test-container`, 필요한 실행 환경에 `make compose-check`·`make up`·`make smoke`를 사용한다. 모두 기존 `uv run --locked` 규칙을 따른다. 새 원시 검사 명령이 필요하면 Makefile에 추가하고 CI도 같은 진입점을 사용한다.
위 도메인·DB·API·전체 회귀·Scalar 검증을 실행했다. 실제 결과는 아래 검수 결과 절을 따른다. 대량 데이터 실행 계획·성능, commit 응답 유실 복구는 검증 범위 밖이다.

## 리뷰와 완료 기준

- 커밋 전 전체 대상의 기준 커밋·패치 식별자를 고정하고 AGENTS.md의 security-diff-scan과 review-agent 전체 절차를 수행한다.
- 문제 후보가 나오면 동일 패치·증거·요구사항으로 별도 읽기 전용 서브에이전트 2개에 병렬 재검토를 요청한다. 사용자와 수정 방향·범위를 합의한 뒤 수정하고 검사·두 리뷰를 다시 수행한다.
- 필수 리뷰 완료와 커밋·푸시 허가는 별개다. 계획 확정 후 사용자가 구현·테스트·Scalar 검수를 요청해 해당 범위를 수행했다. 별도 구조 리팩터링·커밋·푸시는 수행하지 않았다.
- 완료 기준: 합의한 기능·API·예제·DB 원자성·최신순 경계를 구현하고 관련 및 전체 검사 결과를 기능 문서에 연결한다. README의 실행·접속·보존·구현 범위를 비교해 영향 부분만 갱신한다.


## 구현·검수 결과

2026-10-12에 전용 워크트리에서 Network·NetworkLog를 구현하고 검수했다. 마지막 원격 fetch의 main은 기준 `000b7e1a01e7c9e1c6c74e4026d1ab957d138556`과 같아 추가 병합이 필요 없었다.

- 제공 범위: Network CRUD와 이력 목록·단건 7개 작업, 정규화 이름·코드 UNIQUE, 전체 자동 코드 추출, 코드 불변·no-op, 물리 삭제·이력 보존·재등록 UUID 분리, 행 잠금·변경/로그 원자성, 두 목록의 최신순 cursor.
- 기준 파일·경로는 위 계획대로 추가했다. 공통 수정은 차원 등록·ORM 등록·오류 카탈로그·fixture 등록·Scalar의 Network 준비 안내 및 새 head로 기존 병합 검사 경로를 확장하는 범위다. 공통 UoW·기존 차원 업무 규칙은 변경하지 않았다. 의존성·버전·잠금 파일도 변경하지 않았다.
- `make check`: Ruff 린트·포맷, Pyrefly 경고 이상 검사 모두 통과(0 diagnostics).
- `make test-unit`: DB 없는 전체 단위 테스트 328개 통과.
- `make test-container`: 실제 전용 PostgreSQL에서 전체 테스트 **736개 통과**(43.56초). 빈 DB 마이그레이션과 ORM 일치 검사도 통과했다. 최종 영속성 검사 파일의 SHA-256이 워크트리와 검사 이미지에서 일치함을 확인했다. 기존 네 차원 회귀·각 기능 격리·전체 앱 조립·UoW 정리와 Network 도메인·API·OpenAPI·영속성·동시성·마이그레이션을 포함한다.
- 추가 DB 직접 쓰기 검사의 초기 실행은 길이 초과 예외의 Python 타입을 잘못 예상해 2건 실패했다. 실제 DB는 해당 입력을 거부했다. 테스트를 완화하지 않고 CHECK 위반 SQLSTATE 23514와 VARCHAR 길이 초과 22001을 각각 확인하도록 수정했고 위 최종 전체 검사에서 통과했다.
- `make compose-check`, `make up`, `make smoke`: 전용 프로젝트에서 설정·마이그레이션·API 시작·Scalar/OpenAPI HTTP·PostgreSQL SELECT 1·Redis PING 검사 통과.
- `git diff --check`, 문서 링크·앵커·템플릿·규칙 일치 검사를 수행했다. 실행 전제·접속 주소·선택적 override·데이터 보존·구현 범위 변화는 README와 비교해 반영했다.

### Scalar 실제 브라우저 검수

전용 환경은 `mdm-network-8`, `mdm-network-8-api`, API `http://127.0.0.1:18008/docs`, PostgreSQL `127.0.0.1:15438`, 개발 DB `mdm_network_8`과 전용 볼륨, 테스트 DB `mdm_test`의 별도 tmpfs 서비스다. 실제 실행 변수는 README의 전용 환경 안내를 따른다. 기존 다른 프로젝트는 종료·초기화하지 않았다.

| 동작 | 관찰한 결과 |
| --- | --- |
| 새 문서 렌더링 | Network·NetworkLog 등록과 입력·정렬 설명, 31개 생성·14개 수정 예제 선택 메뉴, 구체 응답 모델·실제 UUID 복사 절차 표시 |
| 코드 생략 생성·두 번째 규격 | LTE와 5G 각각 201, 이름·코드 정규화 및 실제 UUID 발급 |
| 자동 코드 충돌 | L T E → 기존 LTE와 충돌, 409 DIMENSION_AUTO_CODE_DUPLICATE |
| 명시 null | code=null은 생략과 구분, 422 VALIDATION_ERROR·body.code |
| 최신순 페이지 | 5G → LTE 순서로 조회하고 첫 페이지 응답 cursor를 복사해 다음 페이지 200·마지막 페이지 null/false 확인 |
| 첫 페이지 cursor 생략 | 새 UI의 생성 cURL과 클라이언트 체크 상태, 실제 서버 요청의 /networks?limit=1 및 대상 로그의 ?limit=1/100에 cursor 없음 |
| 잘못된 cursor | 직접 not-a-cursor를 입력해 400 INVALID_CURSOR |
| no-op | 현재 LTE에 lte 입력 시 200·updated_at 유지·이력 미추가 |
| 실제 이름 수정 | LTE ADVANCED로 변경 200·코드 LTE 유지 |
| 이름 중복 수정 | 기존 5G로 변경 시 409 NETWORK_NAME_DUPLICATE·원본 유지 |
| 삭제 | 직접 생성한 테스트 Network를 삭제해 204·빈 본문 확인 |
| 삭제 후 이력 | 원래 UUID로 200, delete → update → create 및 생성 전/삭제 후 null 확인. no-op·실패 이력 없음 |
| 이력 다음 페이지·단건 | 실제 이력 cursor로 delete 뒤 update/create 조회, 실제 로그 UUID 단건 200 및 조회/변경 요청 ID 구분 |
| 최종 새 UI | 보강한 code 1~20자·null/기호 설명·Network 준비 안내를 확인하고 기본 목록 요청으로 200 실행 |

브라우저 증빙은 로컬 임시 산출물 `/private/tmp/network8-scalar-final.jpg`(최종 기본 목록·200·cursor 생략)과 `/private/tmp/network8-scalar-history.jpg`(삭제 이력 단건)로 저장했다. 전체 동작을 자동 브라우저 회귀 검사로 구성한 것은 아니며 변경마다 실제 UI 검수를 수행해야 한다.

### 남은 범위

- 대량 데이터 EXPLAIN·성능, 실제 commit 순서 보장·순회 전체 스냅샷 일관성, commit 응답 유실의 복구는 보장·검증하지 않는다. 합의한 범위의 제한이다.
- 이번 요청은 구현·테스트·Scalar 검수이며 커밋·푸시·PR 게시를 요청하지 않았다. 작업은 미커밋 상태로 남겼다. 최초 구현 검수 시점에는 필수 리뷰를 실행하지 않았으며, 후속 사용자 요청으로 두 리뷰와 독립 재검토를 수행했다. 최종 통합 이후의 결과는 별도 검수·리뷰 보고서에 기록한다.


### 후속 리뷰 수정과 최신 main 통합

- 첫 P3: Network 중복 409 응답 예제의 details 필드 누락을 공통 예제 매핑에서 수정하고 생성 이름·직접 코드·자동 코드 중복 및 수정 이름 중복의 실제 error 객체와 문서 예제를 비교하는 회귀 테스트를 추가했다.
- 두 번째 P3: LTE 생성 예제 재실행 안내가 단일 오류를 보장하던 설명을 수정했다. 이름·자동 코드 동시 중복은 두 409 코드 중 하나이며 우선순위를 보장하지 않는다. 재실행에도 규격·생성 로그가 각각 하나로 유지되는 테스트를 추가했다. 두 후보 모두 별도 독립 검토자 두 명이 동의했고 사용자 승인 후 수정했다.
- 검수 도중 main에 Year 티켓 #7이 병합되어 기준을 `c1f94f6d8f2738cf20a5d29b33b00ef0ed634bf0`으로 fast-forward했다. 공통 문서·조립·ORM·fixture·오류 예제의 Year 변경을 보존하면서 Network를 결합했다.
- 이미 적용한 `0006_network`와 main의 `0006_year_dimension`은 변경하지 않는다. 빈 `0007_merge_network_year`를 추가해 단일 head로 연결하고, 양쪽 선행 head 및 빈 DB에서 데이터·이력 보존을 검증한다.
- 최종 통합 패치에 관련·전체 검사와 보안·코드 리뷰를 수행한다. 커밋·푸시는 별도 승인 범위이며 수행하지 않는다.

최신 main 통합 이후 `make check`(Ruff·포맷·Pyrefly), `make test-container` 전체 **847개**(63.20초), 빈 DB·선행 head별 마이그레이션/ORM 일치, `make up`, `make smoke`, `git diff --check`와 139개 로컬 문서 링크 대상 검사를 통과했다. 전용 런타임의 기존 LTE UUID가 유지되고 Year 목록이 함께 제공됨을 HTTP로 확인했다. 최종 패치의 보안·코드 리뷰 결과는 소스 변경 없이 별도 산출물로 보고한다.


### Category main 통합과 PR 전달 기준

2026-10-12 커밋·푸시·PR 요청 후 main에 Category PR #20이 추가된 것을 확인했다. 사용자가 추가 통합 범위를 명시적으로 승인해 기준을 `c5cea8aacd8a1cced8cdf10a6ce72983a50da8d6`으로 갱신했다. Category·Year·Network 공통 등록·오류 예제·문서를 함께 보존했다. 이미 적용한 Network·Year 병합 `0007_merge_network_year`와 main의 `0007_merge_category_year`를 변경하지 않고, 빈 `0008_merge_dimension_heads`로 두 경로를 단일 head에 연결한다. 통합 검사는 빈 DB, 각 0006, 각 0007, Network·Year 양쪽 0006 및 두 0007 적용 상태에서 Category·Year·Network 데이터·로그 보존과 반복 업그레이드를 확인한다. 기존 병합 자체의 왕복 검사는 해당 이전 리비전을 명시해 유지한다.

사용자가 최종 검사·보안·코드 리뷰 이후 커밋·푸시·main 대상 PR 생성을 승인했다. 최종 검수와 리뷰는 이 기준의 고정 패치에 수행하고 전달 결과는 별도 보고한다.

최신 Category 통합 패치 검증: `make check`, `make test-container` 전체 **997개 통과**(96.92초), `make compose-check`, `make up`, `make smoke`를 통과했다. Scalar를 새로 불러와 Category·Year·Network 문서 등록을 확인하고 기본 Network 목록 요청에서 cursor가 제외된 상태로 실제 HTTP 200을 확인했다. 브라우저 콘솔 오류는 없었다. 보안·코드 리뷰는 이 최종 패치를 고정한 뒤 별도 검수 산출물로 남긴다.
