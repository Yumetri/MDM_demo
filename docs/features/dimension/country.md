# Country

사용자와 합의한 Country CRUD·변경 이력을 구현했다. PostgreSQL을 사용하며 인증·권한·캐시는 포함하지 않는다.
작업은 [이슈 #5](https://github.com/Yumetri/MDM_demo/issues/5), 공통 원칙은 [이슈 #1](https://github.com/Yumetri/MDM_demo/issues/1)을 따른다.

## 제공 기능

- 국가명과 고유코드를 관리하는 독립 Dimension이다.
- Company·Model 등 다른 차원을 직접 참조하지 않는다. 차원 조합은 추후 Fact에서 처리한다.
- 국가명은 한국어명·영문명으로 나누지 않고 `name` 하나로 관리한다.
- CRUD 경로는 `/countries`, `/countries/{country_id}`이며 변경 이력은 [CountryLog](country-log.md)에서 제공한다.
- API 계약은 [API 규약](../../api-conventions.md)에서 관리한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 국가명 필드 | `name` 하나로 관리 | 사용자 합의 |
| 국가명 검증 | 양끝 공백 제거·대문자 변환·NFC 정규화 후 1~100자. 내부 공백·한글 보존. NUL·UTF-8로 표현할 수 없는 단독 surrogate는 거부 | 사용자 합의 |
| 국가명 중복 | 중복 불허. 양끝 공백 제거·대문자 변환·NFC 정규화 후 동일한 이름은 중복으로 취급. 대소문자만 다른 이름도 중복. 다른 언어의 이름이 같은 국가인지 판단하지 않음 | 사용자 합의 |
| 유니코드 정규화 | NFC를 적용하여 정준적으로 동등한 완성형·분해형 문자열을 동일하게 저장·비교 | 사용자 합의 |
| 국가명 저장 예시 | ` Korea `·`korea`·`KOREA`는 모두 `KOREA`로 저장. `대한민국`은 그대로 저장 | 사용자 합의 |
| DB 유일성 제약 | 정규화된 `name`과 `code` 각각에 독립적인 UNIQUE 제약을 적용하여 동시 요청의 중복도 방지 | 사용자 합의 |
| 코드 입력 | 생성 시 직접 입력 필수. 자동 생성 기능을 제공하지 않음 | 사용자 합의 |
| 직접 코드 형식 | 양끝 공백 제거 후 ASCII 영문 정확히 3자, 대문자로 정규화 | 사용자 합의 |
| 코드 예시 | ` kor `는 `KOR`로 저장. 숫자·내부 공백·길이 위반은 거부 | 사용자 합의 |
| 코드 의미 검증 | 국제 표준 국가코드 존재 여부 및 국가명과의 대응은 검사하지 않음 | 사용자 합의 |
| 코드 유일성 | Country 테이블 안에서 유일해야 함 | 상위 이슈 공통 원칙 |
| 수정 가능 항목 | 국가명만 수정 가능. 등록한 코드는 변경 불가이며 이름 수정 후에도 유지 | 사용자 합의 |
| 동일 값 수정 | 정규화 후 이름이 같으면 성공 응답. 데이터·수정 시각·이력 변경 없음 | 사용자 합의 |
| 삭제 | 물리 삭제하되 변경 이력은 보존 | 사용자 합의 |
| 삭제 후 재등록 | 삭제한 이름·코드 재사용 허용. 새 UUID를 발급하여 이전 대상의 이력과 구분 | 사용자 합의 |
| 초기 데이터 | 빈 테이블로 시작하며 API로 직접 등록. 표준 국가 목록·초기 데이터 자동 삽입은 범위 밖 | 사용자 합의 |
| 동시 수정·삭제 | 행 잠금 획득 후 최신 값을 읽어 순서대로 처리. 나중에 성공한 수정이 최종 값이며 오래된 클라이언트 값 자체를 별도 거부하지 않음 | 사용자 합의 |

Country는 상위 이슈의 코드 선택 입력·자동 생성 원칙에 대한 명시적인 예외다. 상위 이슈 본문은 아직 이 예외를 반영하지 않았다.

이름·코드 중복은 각각 구분한 오류로 반환하며 HTTP 계약은 API 규약을 따른다.

## 처리 흐름

1. 생성 입력의 이름·코드를 검증·정규화한다. 수정은 코드 입력을 허용하지 않는다.
2. 새 UoW를 열고, 수정·삭제는 대상 행 잠금 획득 후 최신 값을 읽어 변경 전 스냅샷을 만든다.
3. 생성 또는 도메인의 이름 변경을 수행한다. 수정 이름도 같은 규칙으로 검증·정규화한다.
4. 정규화 후 이름이 같으면 데이터·수정 시각·로그를 변경하지 않고 성공 응답한다.
5. 생성·실제 이름 변경·물리 삭제와 해당 로그를 같은 세션에 저장한다. DB UNIQUE가 이름·코드 중복을 차단하고 실패한 변경·로그는 함께 rollback한다.
6. 변경과 로그 저장이 성공하면 유스케이스에서 명시적으로 commit한다.
7. 원본 삭제 후에도 이전 UUID의 이력을 보존하며, 삭제한 이름·코드로 재등록하면 새 UUID를 발급한다.

## 데이터와 트랜잭션

- Country는 다른 Dimension의 FK를 두지 않는다.
- 애플리케이션이 국가명과 코드를 정규화하며 각각 DB UNIQUE 제약을 둔다. name은 C collation으로 저장 값 자체를 비교한다. DB에 직접 쓰는 관리 SQL의 대문자·NFC 변환까지 DB가 수행하지는 않는다. 생성·수정 시 모두 유일성을 보장한다.
- 변경과 변경 이력은 같은 UoW·DB 트랜잭션에서 함께 commit/rollback한다.
- 물리 삭제 후에도 원래 UUID의 이력을 보존하며, 재등록한 새 UUID의 이력과 분리한다.
- 이력은 전용 `country_logs`에 기존 ModelLog와 같은 구조로 저장한다. 세부 사항은 [CountryLog](country-log.md)를 따른다.
- 수정·삭제는 기존 Company·Model처럼 SELECT FOR UPDATE로 직렬 처리한다. 별도 버전 검사로 오래된 화면의 수정 요청을 거부하지 않는다.
- 동시 생성·이름 수정의 중복은 DB UNIQUE 제약으로 차단하며, 실패한 변경과 로그는 함께 rollback한다.
- 초기 데이터를 자동 삽입하지 않는다. `countries`는 UUID v4, name, code, UTC 생성·수정 시각을 저장한다. [마이그레이션](../../../migrations/versions/0004_country_dimension.py)은 기존 `0003` 다음에 `0004_country`를 적용한다. [병합 리비전](../../../migrations/versions/0005_merge_brand_country.py)은 Brand의 `0004`와 Country의 `0004_country`를 하나의 head로 연결하며 기존 리비전은 유지한다.

## 조회와 인덱스

- 목록은 생성 시각·UUID 오름차순으로 정렬하고 cursor로 조회한다. 기본 20개·최대 100개를 반환하는 기존 방식으로 합의했다.
- 검색·선택 정렬·총 개수는 이번 범위에서 제외한다.
- PK(id), UNIQUE(name), UNIQUE(code), 목록용 (created_at, id) 인덱스를 둔다. 목록 cursor는 Country 전용 조회·정렬 범위에 묶고 이력·다른 차원의 cursor와 구분한다.
- 상세 HTTP 계약은 API 규약에서 관리한다. 동작은 실제 PostgreSQL 통합 테스트로 검증했다. 대량 데이터의 실행 계획·성능 측정은 수행하지 않았다.

## 캐시

Country·CountryLog 조회에는 캐시를 적용하지 않는다. PostgreSQL에서 직접 읽는다. 캐시 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다. 기존 Redis 서비스는 유지한다.

## 구현과 검증

| 계층 | 구현 |
| --- | --- |
| 도메인 | [Country](../../../src/mdm_demo/domain/entities/country.py), [이름](../../../src/mdm_demo/domain/value_objects/country_name.py), [코드](../../../src/mdm_demo/domain/value_objects/country_code.py) |
| 유스케이스 | [CountryService](../../../src/mdm_demo/application/use_cases/country.py), [UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/country.py) |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/country.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/country_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/country_repository.py) |
| HTTP | [라우터](../../../src/mdm_demo/presentation/routers/country.py), [요청·응답](../../../src/mdm_demo/presentation/schemas/country.py), [실행 예제](../../../src/mdm_demo/presentation/schemas/country_examples.py) |

- [도메인 테스트](../../../tests/unit/domain/test_country.py): 대문자·NFC, 정규화 후 길이, NUL/surrogate, 코드 형식·불변성, no-op·스냅샷.
- [유스케이스 테스트](../../../tests/unit/application/test_country.py): 생성·수정 중복 오류 변환, 동일 값 수정의 commit·로그 생략.
- [PostgreSQL 통합 테스트](../../../tests/integration/persistence/test_country.py): Mapper 왕복, 동시 이름·코드 중복, 행 잠금, 서로 다른 행의 같은 이름 수정, rollback·취소·commit 실패·로그 불변성.
- [병합 마이그레이션 테스트](../../../tests/integration/persistence/test_dimension_merge_migration.py): Brand만·Country만·양쪽 리비전 및 기존 공통 스키마에서 단일 head로 업그레이드하고 기존 데이터·이력을 보존한다. 병합 리비전만 되돌린 뒤 재적용하는 경로도 검사한다.
- [마이그레이션 테스트](../../../tests/integration/persistence/test_country_migration.py): upgrade/downgrade, Company·Model 데이터 보존, ORM 일치 검사.
- [API 테스트](../../../tests/api/test_country.py)·[OpenAPI 예제 실행](../../../tests/api/test_country_openapi_examples.py): CRUD·재사용·중복·검증 오류·cursor 경계와 응답 계약.
- 실제 Scalar 브라우저에서 예제 선택, 생성·수정·삭제·이력 조회, 중복·입력 오류, no-op, 실제 cursor 다음 페이지와 오류를 확인했다. 첫 페이지 생성 코드와 실제 요청에서 cursor 생략을 확인했다.

검사 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다. Company·Model·Brand 회귀를 포함한 전체 테스트를 실행한다. 새 의존성·초기 데이터는 추가하지 않았다.

## 관련 기능

- [Company](company.md)·[Model](model.md): 독립된 다른 차원. 개별 차원의 입력·변경 규칙을 Country에 자동 적용하지 않는다.
- [CountryLog](country-log.md): Country 변경과 함께 저장하고 원본 삭제 후에도 보존하는 이력.
- [Dimension 목차](README.md)

트랜잭션 조립은 [Country UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/country.py)를 사용한다. 차원과 로그 저장소는 같은 세션을 공유하고, 세션 정리·commit·rollback은 [공통 구현](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)에서 처리한다.
