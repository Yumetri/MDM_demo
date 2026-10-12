# Category

사용자와 합의한 독립 단일 단계 Category CRUD·변경 이력을 구현했다. PostgreSQL을 사용하며 인증·권한·캐시는 포함하지 않는다. [6번 구현 계획과 검증 결과](../../plans/issue-6-category.md)를 따른다.
작업은 [이슈 #6](https://github.com/Yumetri/MDM_demo/issues/6), 공통 원칙은 [이슈 #1](https://github.com/Yumetri/MDM_demo/issues/1)을 따른다.

## 제공 기능

- 사용자와 목적: 제품 종류를 단일 단계로 분류하는 독립 Dimension을 관리한다.
- 업무 필드는 name·code이며 시스템 필드는 id·created_at·updated_at이다. 계층 구조·다른 차원과의 참조 관계·추가 업무 필드는 이번 범위에서 제외한다.
- 처리 결과: 분류 생성·조회·이름 수정·물리 삭제와 [CategoryLog](category-log.md)의 변경 이력.
- 진입점: 합의한 경로와 HTTP 계약은 [API 규약의 Category 절](../../api-conventions.md#category-http-계약)을 따른다.
- 인증·권한·업무 캐시는 이번 범위에서 제외한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 분류 구조 | 독립된 단일 단계 분류 | 사용자 합의 |
| 이름 저장 | 양끝 공백 제거 → 대문자 변환 → NFC 정규화. 한글·내부 공백 보존 | 사용자 합의 |
| 이름 길이 | 모든 정규화를 마친 값 기준 1~100자 | 사용자 합의 |
| 이름 유일성 | 정규화된 이름 중복 불허. 이름의 의미·동의어·언어 간 동일성은 판단하지 않음 | 정규화된 값 기준 유일성 합의 |
| 이름 예시 | Smartphone·smartphone·양끝 공백을 포함한 Smartphone은 SMARTPHONE으로 저장·비교 | 사용자 합의 |
| 직접 코드 | 양끝 공백 제거 후 ASCII 영문·숫자 정확히 3자, 대문자로 저장 | 사용자 합의 |
| 코드 유일성 | Category 테이블 안에서 유일하며 정규화 후 값을 비교 | 사용자 합의·상위 이슈 |
| 자동 코드 | 생략 시 정규화한 이름의 ASCII 영문·숫자만 추출한 앞 3자 사용. SMARTPHONE → SMA | 사용자 합의 |
| 자동 생성 실패 | 추출 결과 3자 미만 또는 생성 코드 중복이면 실패하고 직접 입력 안내. 다른 코드 자동 재생성 없음 | 사용자 합의 |
| 수정 | 이름만 변경. 등록된 코드는 불변이며 이름 변경 후에도 유지 | 사용자 합의 |
| 동일 값 수정 | 정규화한 이름이 같으면 성공. 데이터·수정 시각·이력 유지 | 사용자 합의 |
| 삭제 | 물리 삭제하며 원래 UUID의 이력은 보존 | 사용자 합의 |
| 재등록 | 삭제한 이름·코드 재사용 허용. 새 UUID로 이전 이력과 분리 | 사용자 합의 |
| 동시 수정·삭제 | 대상 행을 잠그고 최신 값으로 처리. 나중에 성공한 수정 값을 유지하며 별도 버전 검사 없음 | 사용자 합의 |
| 생성·실제 변경·삭제 | Category 변경과 로그를 같은 UoW·DB 트랜잭션으로 저장 | 사용자 합의·상위 이슈 |

## 처리 흐름

아래 흐름은 실제 PostgreSQL 통합·API 테스트로 검증했다.

1. 이름을 정규화·검증하고 직접 코드를 검증하거나 생략된 코드를 도메인에서 자동 생성한다.
2. 유스케이스에서 새 UoW를 연다. 수정·삭제는 SELECT FOR UPDATE로 잠근 뒤 최신 대상과 변경 전 스냅샷을 읽는다.
3. 생성 또는 도메인의 이름 변경을 수행한다. 정규화 후 같은 이름이면 쓰기·로그·commit 없이 성공 결과를 반환한다.
4. 생성·실제 수정·삭제와 로그를 같은 세션에 저장한다. DB UNIQUE로 이름·코드의 동시 중복을 차단한다.
5. 두 저장이 성공한 뒤 명시적으로 commit한다. 알려진 중복 제약만 해당 오류로 변환하고 다른 DB 오류는 공통 오류 처리로 전달한다.
6. 실패·미커밋 종료·취소·commit 실패에는 공통 UoW를 통해 rollback·세션 정리를 보장한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| categories  | 조회·생성·이름 수정·삭제 | 독립 Category Aggregate |
| category_logs  | 변경 시 추가·조회 | 변경과 원자적으로 저장하는 전용 이력 |

- 구현: Category는 UUID v4, 정규화한 이름·코드, UTC 생성·수정 시각을 저장한다.
- 정규화는 도메인 VO에서 수행하고, DB에는 정규화된 name·code 각각의 UNIQUE와 길이·코드 형식 CHECK를 둔다. Country와 같은 C collation으로 저장 문자열을 비교한다.
- 관리 SQL의 임의 입력까지 DB가 대문자·NFC로 변환하는 구조는 계획하지 않는다. API 경로의 도메인 정규화와 DB 유일성 제약의 역할을 구분한다.
- CategoryUnitOfWork는 데이터·로그 저장소를 한 세션에 묶는다. 로그 조회는 로그 저장소만 요구하는 CategoryLogUnitOfWork Protocol을 사용한다.
- 취소·commit 실패·미커밋 정리는 [공통 SQLAlchemy UoW](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)를 재사용한다.
- 로그의 FK 없는 대상 UUID, 스냅샷, 추가 전용 제약은 [CategoryLog](category-log.md)의 구현 설계를 따른다.

## 조회와 인덱스

| 조회 | 조건 | 인덱스·제약 | 역할 |
| --- | --- | --- | --- |
| 단건·수정·삭제 | Category UUID | PK(id) | 대상 식별·행 잠금 |
| 이름 중복 | 정규화된 name | UNIQUE(name) | 동시 생성·이름 수정의 유일성 |
| 코드 중복 | 정규화된 code | UNIQUE(code) | 동시 생성의 유일성 |
| 목록 | created_at·id 경계 | (created_at, id) | 고정 정렬의 keyset 조회 |

- 목록은 생성 시각·UUID 오름차순이다. 페이지 크기·cursor 계약은 API 규약에서 관리한다.
- 검색·사용자 지정 정렬·총 개수는 제외한다. cursor는 Category 전용 조회·정렬 범위에 묶어 다른 차원·이력과 구분한다.
- 인덱스·cursor 동작은 테스트로 확인했다. 대량 데이터의 실행 계획·성능은 미확인이다.

## 캐시

사용하지 않는다. PostgreSQL에서 직접 읽으며 키·TTL·적재·무효화·Redis 장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치·검증 내용 |
| --- | --- |
| 도메인 | [Category](../../../src/mdm_demo/domain/entities/category.py), [이름 VO](../../../src/mdm_demo/domain/value_objects/category_name.py), [코드 VO](../../../src/mdm_demo/domain/value_objects/category_code.py) — 정규화·자동 코드·불변 코드·no-op |
| 유스케이스 | [CategoryUseCases](../../../src/mdm_demo/application/use_cases/category.py), [UoW Protocol](../../../src/mdm_demo/application/ports/units_of_work/category.py) — 변경·로그 원자성·오류 변환 |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/category.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/category_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/category_repository.py), [UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/category.py) |
| 마이그레이션 | [0006_category](../../../migrations/versions/0006_category_dimension.py) — 기준 병합 head 이후의 독립 테이블·추가 전용 로그 |
| HTTP·조립 | [라우터](../../../src/mdm_demo/presentation/routers/category.py), [스키마](../../../src/mdm_demo/presentation/schemas/category.py), [예제](../../../src/mdm_demo/presentation/schemas/category_examples.py), [조립](../../../src/mdm_demo/composition/category.py) |
| 단위 검증 | [도메인](../../../tests/unit/domain/test_category.py), [유스케이스](../../../tests/unit/application/test_category.py), [cursor](../../../tests/unit/application/test_category_cursor.py) |
| DB 검증 | [영속성](../../../tests/integration/persistence/test_category.py), [마이그레이션](../../../tests/integration/persistence/test_category_migration.py) — 동시 중복·행 잠금·로그 실패·취소·commit 실패·기존 데이터 보존 |
| API 검증 | [CRUD](../../../tests/api/test_category.py), [OpenAPI 예제 실행](../../../tests/api/test_category_openapi_examples.py), [기능 격리](../../../tests/api/test_feature_composition.py) |

- 2026-10-12 `make check`, `make test-unit` 323개, `make test-container` 전체 725개, `make compose-check`, `make up`, `make smoke`가 통과했다. 단위 테스트는 전체 테스트에 포함된다.
- 실제 Scalar에서 예제를 선택하고 생성·중복·입력 오류·단건·수정·no-op·삭제·삭제 후 이력·실제 cursor 페이지 순회를 검증했다. 첫 페이지 생성 코드와 실제 요청에서 cursor가 생략된다.
- 검사 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다. 실행 자원은 [작업 계획](../../plans/issue-6-category.md)의 Category 전용 Compose 프로젝트로 격리했다.
- 대량 데이터 실행 계획·성능, 인증·권한은 이번 검증 범위 밖이다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [CategoryLog](category-log.md) | 변경과 함께 저장하고 원본 삭제 후에도 조회하는 이력 |
| [Country](country.md) | 이름 정규화·유일성·동시성의 참고 구현 |
| [Brand](brand.md) | 영숫자 코드·자동 생성의 참고 구현 |

[Dimension 목차](README.md)
