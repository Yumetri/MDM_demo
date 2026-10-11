# CountryLog

기존 [ModelLog](model-log.md)와 같은 구조의 Country 전용 변경 이력을 구현했다.

## 제공 기능

- Country 생성·수정·삭제 전후 값을 전용 `country_logs` 테이블에 보존한다.
- Country별 이력 목록과 로그 단건 조회를 제공한다. 로그 자체를 수정·삭제하는 기능은 제공하지 않는다.
- 경로는 `/countries/{country_id}/logs`, `/country-logs/{log_id}`로 합의했다. 상세 HTTP 계약은 [API 규약](../../api-conventions.md)에서 관리한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 생성 | 이전 값 없음 → 생성된 값 | 사용자 합의·상위 이슈 |
| 수정 | 변경 전 값 → 변경 후 값 | 사용자 합의·상위 이슈 |
| 삭제 | 삭제 전 값 → 이후 값 없음 | 사용자 합의·상위 이슈 |
| 동일 값 수정 | 정규화 후 국가명이 같으면 로그를 남기지 않음 | 사용자 합의 |
| 스냅샷 | 변경 전·후 전체 `id/name/code` 값 | 사용자 합의 |
| 로그 필드 | 로그 식별자, 대상 Country UUID, 작업 종류, 기록 시각, request ID, 변경 전·후 스냅샷 | 기존 ModelLog 구조 적용 합의 |
| 로그 변경 | 추가 전용. 수정·삭제 불가 | 사용자 합의 |
| 원본 삭제·재등록 | 원래 UUID의 이력을 보존하고 새 UUID의 이력과 분리 | 사용자 합의 |

## 처리 흐름

1. Country 유스케이스가 변경 전·후 스냅샷과 요청의 request ID를 준비한다.
2. CountryLog를 생성해 Country 변경과 같은 UoW·DB 트랜잭션에서 저장한다.
3. 두 저장이 성공하면 명시적으로 commit하고, 실패하면 함께 rollback한다.
4. 원본 Country가 삭제되어도 해당 UUID로 이력을 조회한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| `country_logs` | 추가·조회 | Country 전용 변경 이력 |
| `countries` | 변경 유스케이스에서 조회·변경 | Country 변경과 로그 저장의 원자성 |

- 기존 ModelLog와 같이 대상 UUID는 FK 없이 보존하고 전후 값은 JSONB에 저장한다.
- ModelLog와 같이 Repository에서 추가·조회만 제공하고 DB 트리거로 UPDATE·DELETE를 거부한다. DB 관리자에 의한 TRUNCATE·트리거 제거까지 막는 보안 체계는 아니다.
- request ID는 변경 요청의 추적 값이며 사용자 식별자나 멱등성 키가 아니다.
- Country 수정·삭제의 행 잠금 획득 후 읽은 최신 값으로 전후 스냅샷을 만든다. 각 실제 변경과 로그를 함께 저장하고 실패 시 함께 rollback한다.

## 조회와 인덱스

- Country별 이력 목록과 로그 식별자 단건 조회를 제공한다.
- 목록은 기록 시각·UUID 오름차순으로 정렬하고 cursor로 조회한다. 기본 20개·최대 100개이며, 검색·선택 정렬·총 개수는 이번 범위에서 제외한다.
- 로그 단건은 PK(id), 대상별 목록은 (country_id, occurred_at, id) 인덱스를 사용한다. 이력 cursor는 조회·정렬·대상 Country UUID에 묶고 다른 대상·목록의 cursor를 거부한다.
- 상세 HTTP 계약은 API 규약에서 관리한다.
- 실제 PostgreSQL의 조회·cursor 동작을 검증했다. 대량 데이터의 실행 계획·성능 측정은 수행하지 않았다.

## 캐시

캐시를 적용하지 않고 PostgreSQL에서 직접 조회한다. 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다.

## 구현과 검증

- [엔티티](../../../src/mdm_demo/domain/entities/country_log.py), [조회 유스케이스](../../../src/mdm_demo/application/use_cases/country_log.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/country_log_repository.py), [라우터](../../../src/mdm_demo/presentation/routers/country_log.py)를 구현했다.
- [통합 테스트](../../../tests/integration/persistence/test_country.py)·[이력 API 테스트](../../../tests/api/test_country_log.py)로 생성·수정·삭제 스냅샷, no-op 로그 생략, 로그 수정·삭제 거부, 원자적 rollback, 삭제 후 조회와 재등록 이력 분리를 검증했다.
- Scalar에서도 삭제된 UUID의 전체 이력과 삭제 로그 단건을 조회해 전후 값 보존을 확인했다.
- 실행 전제와 검사 진입점은 [README](../../../README.md)·[Makefile](../../../Makefile), 필수 검증·리뷰는 [AGENTS.md](../../../AGENTS.md)를 따른다.

## 관련 기능

- [Country](country.md): 이력과 함께 저장하는 독립 국가 차원.
- [ModelLog](model-log.md): 합의한 로그 구조의 기존 구현 근거.
- [Dimension 목차](README.md)

트랜잭션 조립은 [Country UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/country.py)를 사용한다. 차원과 로그 저장소는 같은 세션을 공유하고, 세션 정리·commit·rollback은 [공통 구현](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)에서 처리한다.

로그 조회 유스케이스는 [CountryLogUnitOfWork](../../../src/mdm_demo/application/ports/units_of_work/country.py)에 의존하며 로그 저장소만 요구한다. 실행 시 기존 차원별 SQLAlchemy UoW를 그대로 사용할 수 있다. 이는 의존하는 저장소의 범위를 좁히는 타입 계약이며 DB 읽기 전용 권한을 부여하는 장치는 아니다.
