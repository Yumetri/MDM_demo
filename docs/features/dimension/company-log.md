# CompanyLog

차원별 전용 로그 테이블로 분리한다는 합의에 따라 Company 이력은 `company_logs`에 저장한다. 다른 차원의 로그 테이블·스냅샷은 각 차원의 구현 시 추가하며, 공통 물리 로그 테이블은 사용하지 않는다.

## 제공 기능

Company의 생성·수정·삭제 이전·이후 값을 보존하고 회사별 이력 목록·로그 단건을 조회한다. 인증·행위자 저장은 이번 범위에서 제외한다. 경로·응답·오류·정렬 계약은 [API 규약](../../api-conventions.md)을 따른다.

## 업무 규칙과 제약

| 작업 | 이전 값 | 이후 값 |
| --- | --- | --- |
| 생성 | null | 생성된 값 |
| 수정 | 변경 전 값 | 변경 후 값 |
| 삭제 | 삭제 전 값 | null |

- 실제 값이 바뀌지 않은 수정은 기록하지 않는다.
- Company 스냅샷은 id/name/code이며 Company 생성·수정 시각은 포함하지 않는다.
- 로그는 추가 전용이다. Repository는 add와 조회만 노출하고 DB 트리거도 일반 UPDATE·DELETE를 거부한다. DB 관리자에 의한 TRUNCATE·트리거 제거까지 차단하는 감사 보안 체계는 아니다.
- Company 삭제 후 같은 코드가 재등록돼도 대상 UUID가 다르므로 기존 이력과 구분한다.

## 처리 흐름

1. Company 유스케이스가 변경 전·후 스냅샷을 만들어 로그를 생성한다.
2. 같은 UoW 세션에서 Company와 로그를 저장한다.
3. 둘 다 성공하면 명시적으로 commit하고, 실패하면 함께 rollback한다.

## 데이터와 트랜잭션

`company_logs`에 UUID 로그 ID, 원래 Company UUID(`company_id`, NOT NULL), 작업 종류, UTC 기록 시각, request ID, 이전·이후 JSONB 스냅샷을 저장한다. 전용 테이블이므로 `dimension` 구분 컬럼은 없다. JSON null 대신 SQL NULL로 스냅샷 부재를 저장하고 작업별 제약조건으로 조합을 검증한다. `company_id`에는 FK를 두지 않는다. 원본 Company가 물리 삭제되어도 이 식별자와 스냅샷을 변경하지 않는다. 현재 Company와의 JOIN은 `company_logs.company_id = companies.id`로 수행할 수 있다. 대상 존재를 DB의 FK로 검증하지 못하는 한계는 있으며, 유스케이스가 Company 변경과 이력 생성을 같은 트랜잭션으로 처리한다.

행위자는 저장하지 않는다. request ID는 서버가 발급한 요청 추적 값이며 사용자 식별자나 멱등성 키가 아니다. 자동 정리·보존 기한은 없으며, 보존 정책 도입은 별도 합의가 필요하다.

## 조회와 인덱스

(company_id, occurred_at, id) 인덱스로 회사별 keyset 조회를 지원하고 로그 PK로 단건을 조회한다. Company를 JOIN하거나 존재 여부를 검사하지 않으므로 삭제된 회사도 조회할 수 있다. 읽기 UoW는 commit하지 않으며 이력을 추가하지 않는다. 대표 규모에서의 실행 계획은 미확인이다. 시각·UUID 정렬이 실제 commit 순서를 보장하지 않는다.

cursor는 회사 UUID와 조회·정렬 식별자를 서명에 포함한다. Company 목록 또는 다른 회사의 이력 cursor는 거부한다. 새 이력이 경계 이후에 추가되면 다음 페이지에 나타날 수 있으며 스냅샷 일관성을 제공하지 않는다. 기존 인덱스와 테이블을 사용하므로 조회 API 추가에 따른 마이그레이션은 없다.

## 캐시

적용하지 않는다. 이력은 PostgreSQL에 영속 저장한다.

## 구현과 검증

- [도메인](../../../src/mdm_demo/domain/entities/company_log.py): 스냅샷 복사·불변화와 작업별 형태 검증.
- [모델](../../../src/mdm_demo/infrastructure/persistence/models/company_log.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/company_log_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/company_log_repository.py).
- [분리 마이그레이션](../../../migrations/versions/0002_split_company_logs.py): 기존 테이블·대상 컬럼 이름을 변경하고 차원 구분 컬럼을 제거한다. Company 이력 ID·시각·request ID·스냅샷은 유지하며 FK는 추가하지 않는다. 인덱스와 추가 전용 트리거도 전용 이름으로 전환한다.
- 이미 적용한 초기 마이그레이션은 보존한다. 초기 단계에서 Company 이외의 로그가 발견되면 오분류하지 않고 분리 마이그레이션을 중단한다. 다운그레이드는 Company 구분값을 복원하여 공통 테이블 형태로 되돌린다.
- [마이그레이션 테스트](../../../tests/integration/persistence/test_log_migration.py): 삭제된 Company의 이력을 포함한 데이터 보존, FK 부재·NOT NULL·인덱스, 업그레이드·다운그레이드 왕복, 다른 차원 발견 시 중단.
- [영속성 테스트](../../../tests/integration/persistence/test_company.py): Mapper 왕복, 함께 commit/rollback, 로그 실패·취소·commit 실패, 동시 변경 이력 연결.
- [API 테스트](../../../tests/api/test_company.py): 변경 없는 수정의 로그 생략, 삭제·재등록 후 과거 이력 보존, request ID 연결.
- [조회 유스케이스](../../../src/mdm_demo/application/use_cases/company_log.py), [조회 라우터](../../../src/mdm_demo/presentation/routers/company_log.py), [로그 cursor](../../../src/mdm_demo/infrastructure/pagination/company_log_cursor.py).
- [조회 API 테스트](../../../tests/api/test_company_log.py): 삭제 후 조회·코드 재사용 시 이력 분리, 생성/수정/삭제 스냅샷, 빈 목록·없는 로그·잘못된 UUID, 같은 시각 페이지 경계, cursor 조건 구분, 읽기 전용 API.
- 실행법은 [README](../../../README.md)의 `make test-container`를 따른다.

## 관련 기능

- [Company](company.md)
- [Dimension 목차](README.md)
