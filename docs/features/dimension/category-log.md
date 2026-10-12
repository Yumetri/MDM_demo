# CategoryLog

사용자와 합의한 Category 전용 추가 전용 로그 저장·조회를 구현했다. 기존 차원과 같은 구조를 사용하며 [6번 구현 계획과 검증 결과](../../plans/issue-6-category.md)를 따른다.

## 제공 기능

- 사용자와 목적: Category 생성·실제 이름 수정·삭제 전후의 값을 추적한다.
- 처리 결과: Category별 이력 목록과 로그 단건 조회. 이력을 수정·삭제하는 API는 제공하지 않는다.
- 진입점과 응답 필드·HTTP 계약은 [API 규약의 Category 절](../../api-conventions.md#category-http-계약)을 따른다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 생성 | 이전 값 없음 → 생성된 값 | 사용자 합의·상위 이슈 |
| 실제 수정 | 변경 전 값 → 변경 후 값 | 사용자 합의·상위 이슈 |
| 삭제 | 삭제 전 값 → 이후 값 없음 | 사용자 합의·상위 이슈 |
| 동일 값 수정 | 로그를 추가하지 않음 | 사용자 합의 |
| 스냅샷 범위 | id/name/code 전체 값. Category 생성·수정 시각 제외 | 사용자 합의 |
| 기록 정보 | 로그 UUID, 대상 UUID, 작업 종류, UTC 기록 시각, 변경 요청 ID, 이전·이후 값 | 사용자 합의 |
| 보존 | 추가 전용, 수정·삭제·자동 만료 없음 | 사용자 합의 |
| 원본 삭제·재등록 | 원래 UUID의 기록 보존, 재등록한 새 UUID의 이력과 분리 | 사용자 합의 |
| 대상별 조회 | 현재 Category 존재를 검사하지 않으며 삭제된 대상도 조회 | 사용자 합의 |

## 처리 흐름

아래 흐름은 실제 PostgreSQL 통합·API 테스트로 검증했다.

1. Category 유스케이스가 서버 발급 요청 ID와 변경 전·후 스냅샷을 준비한다. 수정·삭제는 행 잠금 후 최신 값을 사용한다.
2. CategoryLog가 로그 UUID·UTC 기록 시각을 부여하고 스냅샷을 복사·불변화한다.
3. Category 변경과 로그를 같은 UoW·트랜잭션에서 저장한 뒤 명시적으로 commit한다. 실패하면 함께 rollback한다.
4. 이력 목록은 원래 대상 UUID로 직접 조회한다. 단건은 로그 UUID로 조회한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| category_logs  | 추가·조회 | Category 전용 이력 |
| categories  | 변경 유스케이스에서만 읽기·쓰기 | 변경과 이력의 원자성 |

- 구현: 대상 UUID는 FK 없이 보존하고 이전·이후 스냅샷은 JSONB에 저장한다. 스냅샷 부재는 SQL NULL로 저장하고 작업 종류별 조합을 CHECK로 검증한다.
- Repository는 추가·조회만 제공하고 DB 트리거로 UPDATE·DELETE를 거부한다. 기존 차원의 방식이며 DB 관리자에 의한 TRUNCATE·트리거 제거를 차단하는 체계는 아니다.
- 변경 요청 ID는 추적 값이며 행위자·인증 정보·멱등성 키가 아니다.
- 로그 조회의 UoW Protocol은 로그 저장소만 요구한다. 실제 구현에서는 Category별 SQLAlchemy UoW와 공통 세션 정리를 재사용한다.

## 조회와 인덱스

| 조회 | 조건 | 인덱스 | 역할 |
| --- | --- | --- | --- |
| Category별 목록 | category_id·occurred_at·id 경계 | (category_id, occurred_at, id) | 대상별 keyset 조회 |
| 로그 단건 | 로그 UUID | PK(id) | 단건 식별 |

- 목록은 기록 시각·UUID 오름차순이다. 페이지 크기·없는 대상·오류 계약은 API 규약을 따른다.
- cursor는 조회 종류·정렬·대상 Category UUID에 묶는다. 다른 대상·Category 목록·다른 차원의 cursor를 거부한다.
- 정렬은 실제 commit 순서를 보장하지 않으며 페이지 순회의 스냅샷 일관성도 제공하지 않는다.
- 인덱스·cursor 동작은 테스트로 확인했다. 대량 데이터 실행 계획·성능은 미확인이다.

## 캐시

사용하지 않는다. PostgreSQL에서 직접 조회하며 키·TTL·무효화·캐시 장애 fallback은 해당하지 않는다.

## 구현과 검증

- [CategoryLog](../../../src/mdm_demo/domain/entities/category_log.py)·[ORM](../../../src/mdm_demo/infrastructure/persistence/models/category_log.py)·[Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/category_log_mapper.py)·[Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/category_log_repository.py)로 스냅샷·SQL NULL·추가 전용 제약을 구현했다.
- [조회 유스케이스](../../../src/mdm_demo/application/use_cases/category_log.py)·[라우터](../../../src/mdm_demo/presentation/routers/category_log.py)·[cursor](../../../src/mdm_demo/infrastructure/pagination/category_log_cursor.py)는 대상별 목록·로그 단건·대상 범위 검증을 제공한다.
- [도메인](../../../tests/unit/domain/test_category.py)·[로그 유스케이스](../../../tests/unit/application/test_category_log.py)·[영속성](../../../tests/integration/persistence/test_category.py)·[로그 API](../../../tests/api/test_category_log.py)로 스냅샷 불변성·로그 저장 실패의 원자적 rollback·commit 실패·취소·UPDATE/DELETE 거부·no-op·삭제 후 이력·코드 재사용 분리·cursor 경계를 검증했다.
- 2026-10-12 전체 725개 테스트가 통과했다. 실제 Scalar에서 삭제한 UUID의 이력 3건을 조회하고 limit=1의 실제 cursor로 create→update→delete를 순회했다. 삭제 로그 단건에서 before와 after:null, 변경 요청 ID와 현재 조회 요청 ID의 분리를 확인했다.
- 검사 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다. 성능·DB 관리자에 의한 변경 차단·인증은 검증 대상이 아니다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [Category](category.md) | 같은 트랜잭션에서 변경과 로그를 저장 |
| [CountryLog](country-log.md) | 전용 로그 구조·보존·조회 방식의 참고 구현 |

[Dimension 목차](README.md)
