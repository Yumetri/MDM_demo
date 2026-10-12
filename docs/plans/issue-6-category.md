# 6번 Category 구현 계획

2026-10-12 사용자와 최종 확정한 계획에 따라 Category CRUD·CategoryLog를 구현·검증했다. 아래는 착수 기준과 구현 범위·검증 기록이며 커밋·푸시 승인을 대신하지 않는다.

## 기준과 담당 범위

- 티켓: [#6 Category](https://github.com/Yumetri/MDM_demo/issues/6), 공통 원칙: [#1](https://github.com/Yumetri/MDM_demo/issues/1).
- 기준 브랜치: main. 2026-10-12 fetch 후 origin/main과 HEAD 모두 `000b7e1a01e7c9e1c6c74e4026d1ab957d138556`이다.
- 작업 브랜치: codex/issue-6-category. 워크트리: /Users/tagit/.codex/worktrees/issue-6-category/MDM_demo.
- 담당: 독립된 Category CRUD·CategoryLog 저장·조회·관련 테스트·문서.
- 업무 명세는 [Category](../features/dimension/category.md)·[CategoryLog](../features/dimension/category-log.md), 필드·오류·HTTP 계약은 [API 규약](../api-conventions.md#category-http-계약)에서 관리한다. 이 계획에 상세 규칙을 복제하지 않는다.

## 확인한 기존 구현

- [기능 목록](../../src/mdm_demo/composition/registry.py)의 기본 등록은 Company·Model·Country·Brand다. Category 등록은 없다.
- [Country 이름 VO](../../src/mdm_demo/domain/value_objects/country_name.py)와 [Country Repository](../../src/mdm_demo/infrastructure/persistence/repositories/country_repository.py)는 이름 정규화·유일성·행 잠금의 참고다.
- [Brand 코드 VO](../../src/mdm_demo/domain/value_objects/brand_code.py)와 [Brand 유스케이스](../../src/mdm_demo/application/use_cases/brand.py)는 영숫자 코드 자동 생성 및 직접/자동 코드 중복 구분의 참고다.
- [차원별 UoW Protocol](../../src/mdm_demo/application/ports/units_of_work/country.py), [차원별 SQLAlchemy UoW](../../src/mdm_demo/infrastructure/persistence/units_of_work/country.py), [공통 UoW](../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)를 활용한다.
- [조립 모듈](../../src/mdm_demo/composition/country.py)·[로그 cursor](../../src/mdm_demo/infrastructure/pagination/country_log_cursor.py)·[예제 실행 테스트](../../tests/api/test_country_openapi_examples.py)를 확인했다.
- 기준 코드로 OpenAPI를 직접 생성해 기존 4개 차원·4개 로그 태그, 생성 요청의 이름 있는 예제·null 보존, 선택적 cursor의 자동 입력 예제 없음, DELETE 204 본문 없음과 Category 경로 부재를 확인했다. Category 기능이나 실제 Scalar 브라우저 동작을 검증한 것은 아니다.

## 구현 순서와 파일

아래 Category 전용 파일을 구현했다. 실제 코드·테스트 링크는 기능 문서에 연결했다.

| 단계 | 예정 위치 (src/mdm_demo 기준) | 구현 내용 |
| --- | --- | --- |
| 1. 도메인 | domain/entities/category.py·category_log.py, domain/value_objects/category_name.py·category_code.py, domain/errors/category.py | 이름 정규화·유일성에 필요한 값, 코드 검증·생성·불변성, 이름 변경·동일 값 판단, 로그 불변 스냅샷 |
| 2. 포트·DTO | application/dto/category.py·category_log.py, application/errors/category.py, application/ports/repositories/category_repository.py·category_log_repository.py, application/ports/cursors/category.py, application/ports/units_of_work/category.py | 차원별 타입과 저장소·cursor, 데이터/로그 UoW와 로그 전용 UoW Protocol |
| 3. 영속성 | infrastructure/persistence/models/category.py·category_log.py, mappers/category_mapper.py·category_log_mapper.py, repositories/category_repository.py·category_log_repository.py, units_of_work/category.py | 손실 없는 Mapper, 별도 테이블·UNIQUE·CHECK·인덱스·추가 전용 로그, 같은 세션의 저장소 |
| 4. 유스케이스 | application/use_cases/category.py·category_log.py | CRUD·행 잠금·no-op·원자적 로그, 이름/직접 코드/자동 코드 중복 오류 변환, cursor 목록·이력 단건 |
| 5. HTTP·조립 | presentation/schemas/category.py·category_log.py·category_examples.py, presentation/routers/category.py·category_log.py, presentation/dependencies/category.py, composition/category.py | 공통 envelope·오류·요청 ID 활용, 이름 있는 실행 예제, 기능 모듈 등록 |
| 6. 테스트·문서 | tests/fixtures/category.py 및 기존 테스트 계층, 기능 문서·API 규약·README | 격리·전체 앱·실제 PostgreSQL·Scalar 검증 및 실제 구현 근거 갱신 |

- DB 설계는 categories와 category_logs를 새로 추가한다. 명명은 uq_categories_name·uq_categories_code, ix_categories_created_at_id, ix_category_logs_category_time을 사용하고 Category 전용 CHECK·트리거를 정의할 예정이다.
- 이름 VO는 기존 Country와 같은 NUL·단독 surrogate 거부를 포함할 계획이다. 길이는 upper·NFC 후에 검사하고 NFC 전후 및 대문자 확장으로 길이가 달라지는 경계를 테스트한다.
- 도메인과 ORM·API DTO는 별도 클래스로 유지한다. presentation에서 인프라를 생성하지 않으며 기존 공통 UoW·앱 팩토리를 확장하지 않고 재사용한다.
- 초기 분류 목록·seed는 추가하지 않고 빈 테이블을 API로 관리하는 안이다. 새 의존성은 현재 계획에 없다.

## 공통 파일 변경 범위

| 기존 파일 | 필요한 변경 |
| --- | --- |
| [composition/registry.py](../../src/mdm_demo/composition/registry.py) | Category 모듈 import·목록 등록만 추가 |
| [migrations/env.py](../../migrations/env.py) | Category·CategoryLog ORM 등록만 추가 |
| [presentation/error_catalog.py](../../src/mdm_demo/presentation/error_catalog.py) | 합의한 Category 이름·직접 코드 중복 오류를 추가 |
| [presentation/schemas/examples.py](../../src/mdm_demo/presentation/schemas/examples.py) | 문서 상단 공통 실행 순서를 반복하지 않고 Category 준비·생성 UUID·cursor 안내만 연결. 새 오류가 응답 예제로 생성되는 경로 확인 |
| [tests/conftest.py](../../tests/conftest.py) | Category fixture 플러그인 등록만 추가 |
| [tests/api/test_feature_composition.py](../../tests/api/test_feature_composition.py) | Category의 복수 경로 categories를 명시하고 격리 기능·전체 조립 검증에 포함. categorys가 생성되지 않게 처리 |
| [docs/features/dimension/README.md](../features/dimension/README.md) | Category·CategoryLog 링크 추가 |
| [docs/api-conventions.md](../api-conventions.md) | 합의한 Category 계약을 구현·OpenAPI·테스트와 함께 반영 |
| [README](../../README.md)·[API 문서 기능](../features/api-documentation/api-reference.md) | 실제 구현 후 제공 기능·경로·데이터 보존·마이그레이션 위치·확인한 브라우저 범위 갱신 |

이 변경으로 기존 Company·Model·Brand·Country의 업무 규칙을 바꾸지 않는다. 공통 동작의 구조 변경이 필요해지면 대상·영향을 설명하고 별도 리팩터링 허가를 받는다.

## 병렬 개발·마이그레이션·실행 자원

- 선행 공통 변경 PR #15(차원별 타입)·#16(UoW)·#17(조립)은 기준 main에 병합되어 있다. 현재 열린 PR은 없음을 다시 확인했다.
- 7번 Year·8번 Network·9번 Memory 계획 채팅과 워크트리가 진행 중임을 확인했다. 최신 개별 패치는 확인하지 못했으므로 독립적인 변경이라고 단정하지 않는다.
- 공통 계약·오류 카탈로그·등록 목록·fixture 목록·기능 목차·문서 상단 설명은 다른 차원과 겹칠 수 있다. 최종 리뷰 전 해당 변경 경로를 다시 비교하고 등록·문서 내용을 모두 보존한다.
- Category 고유 마이그레이션 파일·revision ID는 0006_category_dimension.py / 0006_category로 제안한다. 현재 부모는 0005_merge_brand_country이며 작성 시 최신 main과 기존 ID 점유를 다시 확인한다.
- 다른 차원이 같은 부모에서 분기하면 기존 공유 리비전의 ID·부모·내용은 바꾸지 않는다. 스키마 호환성을 검토한 통합 순서에 따라 필요한 merge revision으로 최종 단일 head를 만든다.
- 빈 DB, 기준 head, 각 병렬 선행 head에서 최종 head로 업그레이드하여 기존 데이터·로그 보존과 ORM 일치를 검증한다. downgrade는 격리 DB에서 검증한다.
- Compose 기본 설정은 프로젝트명·이미지명·PostgreSQL 호스트 포트를 공유한다. 워크트리만으로 실행 자원이 격리되지 않으므로 기본 설정으로 바로 실행하지 않는다.
- 실행 전에 점유 상태를 확인하고 Category 전용 Compose 프로젝트명·API/migrate/test 이미지 태그·API 및 PostgreSQL 호스트 포트·DB·볼륨을 분리한 실행용 override를 준비한다. Category 프로젝트의 테스트 DB 이름은 기존 보호 조건인 mdm_test를 유지하되 별도 PostgreSQL 서비스에서 실행한다.
- 다른 작업의 컨테이너·볼륨은 종료·초기화하지 않는다. 실행용 override 파일과 환경 변수를 통해 기존 Makefile 진입점을 사용하며 원시 검사 명령을 문서에 새로 관리하지 않는다.

## 검증 계획

| 영역 | 반드시 확인할 동작 |
| --- | --- |
| 도메인 | trim·upper·NFC 순서, 정규화 후 1/100/101자, 한글·내부 공백, NUL·surrogate, 영숫자 코드·자동 생성 실패·불변 코드, UUID 동등성, no-op, 로그 스냅샷 불변성 |
| 애플리케이션 | 생성·수정·삭제와 로그의 commit 경계, no-op 저장·commit 생략, 이름/직접 코드/자동 코드 오류 변환과 동시 중복 우선순위 없음, 로그 조회의 좁은 UoW 의존성 |
| 실제 PostgreSQL | Mapper 왕복·JSONB/SQL NULL·CHECK, 미커밋·로그 저장 실패·commit 실패·취소·반복 취소 정리, 동시 이름/코드 생성·서로 다른 행의 같은 이름 수정·수정/삭제 경합, 로그 UPDATE/DELETE 거부, 무관한 DB 오류를 중복으로 오인하지 않음 |
| 마이그레이션 | 고유 revision·최종 단일 head, 빈 DB/기준/각 선행 head 업그레이드, 기존 차원·로그 보존, 격리 DB downgrade·재적용, ORM 일치 |
| API·cursor | CRUD·이름/코드 재사용·삭제 후 이력·없는 대상, 엄격한 입력·코드 생략과 null 구분, 정규화 후 이름 중복, no-op 시각·로그 유지, 같은 시각의 UUID 경계·삭제된 경계 행, 다른 차원/목록/대상 cursor 거부·limit 경계 |
| 조립·회귀 | Category 격리 앱과 전체 앱 모두 검증, 기존 4개 차원·로그 회귀, 계층 의존성·중복 라우트·기능 상태 등록·자원 수명 |
| OpenAPI·Scalar | OpenAPI에서 꺼낸 이름 있는 예제의 실제 요청 실행, null·빈 객체 보존, 상태별 예제·204 본문 없음, 실제 브라우저 예제 선택→CRUD→no-op→삭제 후 이력→다음 페이지, 새 UI의 첫 페이지 생성 코드·실제 요청 모두 cursor 생략 |

- 검사 진입점: [Makefile](../../Makefile)의 make check 또는 make check-container, make test-unit, make test-container, make compose-check, make up, make smoke. Category 자원 격리를 적용한 환경에서 수행한다.
- Markdown 변경은 git diff --check 및 링크 대상·계약 간 모순을 확인한다.
- 실행하지 못한 검사와 이유는 별도로 보고하며 테스트 코드의 존재를 검사 통과로 표현하지 않는다. 성능·대량 데이터 실행 계획·인증은 이번 검증 범위에 포함하지 않는다.

## 리뷰·완료 조건

1. 합의한 명세를 구현하고 위 검사와 README 비교를 완료한다.
2. 원격 main과 병렬 변경을 다시 확인·반영하고 관련 검사로 최종 상태를 검증한다.
3. 기준 커밋·전체 패치 식별자를 기록하고 패치를 고정한다. 커밋 전에 AGENTS.md의 security-diff-scan·review-agent 전체 절차를 실행한다. 스킬 누락·실행 실패·검토 누락은 보고하고 커밋하지 않는다.
4. 문제 후보가 있으면 같은 패치·증거를 별도 읽기 전용 서브에이전트 2개가 독립 재검토한다. 주 에이전트가 근거·발생 조건·영향·두 의견·수정안·검증 계획을 보고하고 사용자의 수정 합의 후에만 수정한다.
5. 수정하면 검사와 두 필수 리뷰를 최종 패치에 다시 수행한다. 문제가 없으면 검토 패치와 커밋 대상의 일치를 확인하여 보고한다. 커밋·푸시는 각각 별도 사전 허가 범위에서만 실행한다.

## 현재 검증 상태

- 기존 코드·기능맵·API 규약·생성 OpenAPI를 확인했다. 최신 main과 작업 브랜치는 일치한다.
- Category 런타임·마이그레이션·업무 테스트·실제 Scalar 검증을 완료했다.
- 이번 산출물은 Category 구현·테스트·문서다. 아래 검증 결과와 검증 공백을 구분한다.


## 최초 구현·검증 결과 (2026-10-12, main 병합 전)

- Category 전용 마이그레이션 0006_category는 기존 0005_merge_brand_country를 부모로 사용하며 최초 구현 당시 단일 head였다. 빈 DB·Brand head·Country head·기준 병합 head에서 업그레이드하고 기존 차원·로그 보존, Category downgrade·재적용, ORM 일치를 검증했다.
- 기존 병합 마이그레이션 테스트는 검증 대상 0005_merge_brand_country를 명시하도록 수정하고, 최신 head 검증은 Category 마이그레이션 테스트에서 수행한다.
- Category 실행은 프로젝트 mdm-category-6, 이미지 mdm-category-6-api, 개발 DB mdm_category6, API 8006, PostgreSQL 5436, 프로젝트 전용 영속 볼륨을 사용했다. 실행용 override는 /private/tmp/mdm-category-6.compose.yaml이며 저장소에 포함하지 않았다. 테스트는 같은 프로젝트의 별도 postgres-test 서비스와 mdm_test DB다.
- make compose-check·make up·make smoke·make check가 통과했다. Ruff·포맷·Pyrefly는 경고 포함 진단이 없다. make test-unit 323개, make test-container 전체 725개가 통과했으며 단위 검사는 전체 검사에 포함된다.
- Scalar에서 이름 있는 생성 예제 선택, 정상 생성·단건·수정·삭제, 이름/자동 코드 중복409, null·자동 생성 불가422, 수정 이름 중복409·코드 변경422, no-op 시각 유지, 삭제 후 단건404·로그 목록/단건200을 확인했다.
- 목록의 생성 curl과 실제 첫 요청에는 cursor가 없었다. 실제 응답 cursor로 다음 Category를 조회하고 잘못된 cursor400을 확인했다. 로그 목록도 첫 요청에서 cursor가 없었으며 limit=1의 실제 cursor로 create/update/delete 3건을 순회했다.
- no-op·중복·검증 실패는 로그를 늘리지 않았다. 삭제 로그의 이전 스냅샷·after:null과 변경 요청/조회 요청 ID 분리도 실제 Scalar 응답으로 확인했다.
- 초기 구현의 단독 surrogate 본문 예제가 OpenAPI 직렬화를 실패시켜 이를 문서 본문에서 제거했다. 거부 동작은 실제 API 테스트에 유지했고 수정 후 전체 725개 테스트와 실제 문서 렌더링이 통과했다.
- 대량 데이터 성능·실행 계획, 다른 작업의 아직 병합되지 않은 미래 마이그레이션 통합은 미검증이다. 미래 병합 시 원격 상태를 재확인하고 공통 등록·단일 head·회귀를 다시 검증해야 한다.


## PR #20 충돌 해결·재검증 (2026-10-12)

- main의 Year 기능(PR #19, c1f94f6)을 병합해 Category·Year의 등록부·오류 예제·fixture·문서·기능 목차를 함께 보존했다. 기존 업무 규칙과 두 차원의 공유된 마이그레이션 파일은 변경하지 않았다.
- 최종 head는 [0007_merge_category_year](../../migrations/versions/0007_merge_category_year.py)이며 부모는 0006_category·0006_year_dimension이다. 스키마 변경 없이 두 리비전을 연결한다.
- [병합 테스트](../../tests/integration/persistence/test_category_year_merge_migration.py)로 빈 DB, Category만 적용된 DB, Year만 적용된 DB, 두 부모가 모두 적용된 DB의 업그레이드·기존 행/로그 보존·병합 노드 downgrade/재적용을 확인했다. 기존 Brand·Country 병합 테스트는 해당 리비전을 직접 검사하며 최신 head 검사도 갱신했다.
- make check의 Ruff·포맷·Pyrefly가 통과했고 make test-unit 347개, make test-container 전체 831개가 통과했다. 전체 검사는 실제 PostgreSQL 마이그레이션·ORM 일치 검사와 기존 차원 API 회귀를 포함한다.
- 전용 Category Compose 환경에서 make compose-check·make up·make smoke가 통과했다. 기존 Category DB에서 Year 추가·병합 head 적용 후 앱이 정상 기동했다.
- 실제 Scalar에서 Category·Year 준비 안내와 두 차원·로그 태그가 함께 렌더링됐다. 두 목록의 Test Request→Send 실행은 각각 /categories?limit=1, /years?limit=1로 전송됐고 cursor 생략·200 응답을 확인했다. Category 기본 생성 예제와 요청 코드도 보존됐다.
- 대량 데이터 성능·아직 main에 병합되지 않은 후속 차원과의 통합은 이번 검증 범위에 포함하지 않는다.
