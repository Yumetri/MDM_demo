# YearLog

**구현한 기능**이다. 2026-10-12 합의한 이력·조회·운영 정책을 코드·DB·API·검증에 반영했다.

## 제공 기능

- Year 생성·수정·삭제의 전후 값을 보존한다.
- 삭제 후에도 원래 Year UUID로 이력 목록을 조회하고 로그 UUID로 단건을 조회한다.
- 진입점·응답·HTTP 오류·페이지네이션은 [API 규약의 Year 계약](../../api-conventions.md#yearyearlog-http-계약)을 따른다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 생성 | 이전 값 없음 → 생성 값 | 사용자 합의 |
| 실제 연도 수정 | 변경 전 값 → 변경 후 값. UUID 유지·코드 동시 변경 | 사용자 합의 |
| 같은 연도로 수정 | 로그 추가 없음 | 사용자 합의 |
| 삭제 | 삭제 전 값 → 이후 값 없음 | 사용자 합의 |
| 스냅샷 | id/year/code 전체 값. year는 정수로 보존 | 사용자 합의·Year 입력 타입 |
| 저장 정보 | 대상 UUID·작업 종류·UTC 기록 시각·요청 ID·변경 전후 값 | 사용자 합의 |
| 로그 변경 | 추가 전용. 수정·삭제 거부 | 사용자 합의 |
| 목록 정렬 | 기록 시각 내림차순. 같은 시각은 로그 UUID 내림차순 | 사용자 합의 |
| 목록 크기 | 기본 20개, 허용 1~100개 | 사용자 합의 |
| 삭제·재등록 | 기존 UUID의 이력 보존. 새 UUID의 이력과 분리 | 사용자 합의 |

스냅샷은 id/year/code이며 원본 생성·수정 시각을 제외한다. 로그 자체의 기록 시각은 별도로 저장한다.

## 처리 흐름

1. Year 유스케이스가 변경 전후의 스냅샷과 서버 발급 request ID를 만든다.
2. YearLog가 로그 UUID·UTC 기록 시각을 부여하고 스냅샷을 복사·불변화한다.
3. Year 변경·YearLog 추가를 같은 세션에 저장하고 함께 commit한다.
4. 조회는 읽기 전용으로 수행하며 원본 Year의 존재 여부를 검사하지 않는다. 기록 없는 UUID는 빈 목록을 반환한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| year_logs | 추가·조회 | 이력 식별·원본 대상 식별·작업·시각·요청 ID·이전/이후 JSONB |
| years | 변경 유스케이스에서만 읽기·쓰기 | Year와 이력 저장의 원자성 |

- 원본 대상 UUID는 NOT NULL이며 삭제 후 이력 보존을 위해 FK를 두지 않는다.
- 기존 이력처럼 부재한 스냅샷은 SQL NULL, 존재하는 스냅샷은 JSONB로 저장한다.
- 작업별 before/after 조합 CHECK와 UPDATE·DELETE 거부 트리거를 둔다.
- year 값은 JSON 숫자로 유지한다. 기존 ModelLog의 문자열 전용 스냅샷 타입을 변경하지 않고 Year 전용 타입을 둔다.
- 실패·취소·commit 실패 정리는 기존 공통 UoW를 재사용한다.
- 대상별 목록·단건 조회로 제한하고 검색·필터·총 개수는 제외한다. 로그 자동 만료·행위자·인증·권한·자동 재시도는 추가하지 않는다.

## 조회와 인덱스

| 조회 | 필터·정렬 | 관련 인덱스 | 역할 |
| --- | --- | --- | --- |
| 대상별 목록 | year_id, occurred_at DESC, id DESC | (year_id, occurred_at, id) | UUID별 keyset 조회 |
| 로그 단건 | 로그 UUID | PK(id) | 단건 조회 |

- 이력 목록은 최근 변경을 먼저 보기 위해 기록 시각·로그 UUID 내림차순으로 합의했다. 다음 페이지는 (occurred_at, id)가 마지막 경계보다 작은 구간에서 조회한다. 기존 차원의 이력 정렬은 변경하지 않는다.
- 이력 cursor는 조회 종류·정렬·대상 UUID에 묶는다. 다른 대상·Year 목록·다른 차원 토큰을 거부한다.
- 정렬은 실제 commit 순서·스냅샷 일관성을 보장하지 않는다.
- 실제 실행 계획·대량 데이터 성능은 미확인이다.

## 캐시

캐시 없이 PostgreSQL에서 직접 조회하기로 합의했다. 키·TTL·무효화·Redis fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치 | 역할·검증 |
| --- | --- | --- |
| 도메인 | [YearLog](../../../src/mdm_demo/domain/entities/year_log.py) | 추가 전용 전후 스냅샷·정수 값 보존 |
| 저장 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/year_log.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/year_log_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/year_log_repository.py) | FK 없는 대상·JSONB/SQL NULL·내림차순 조회 |
| 마이그레이션 | [Year 리비전](../../../migrations/versions/0006_year_dimension.py) | CHECK·인덱스·UPDATE/DELETE 거부 트리거 |
| 조회 | [유스케이스](../../../src/mdm_demo/application/use_cases/year_log.py), [라우터](../../../src/mdm_demo/presentation/routers/year_log.py), [cursor](../../../src/mdm_demo/infrastructure/pagination/year_log_cursor.py) | 대상/목록/정렬에 묶은 서명 토큰 |
| 검증 | [도메인](../../../tests/unit/domain/test_year.py), [PostgreSQL](../../../tests/integration/persistence/test_year.py), [API](../../../tests/api/test_year_log.py), [OpenAPI](../../../tests/api/test_year_openapi_examples.py) | 불변성·원자성·삭제 후 조회·재등록 분리·동시 시각 UUID 내림차순·request ID 구분 |

실행 결과·실제 Scalar 검수와 확인하지 않은 범위는 [검증 보고](../../reports/issue-7-validation.md)를 따른다.

검증 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [Year](year.md) | 변경과 이력을 같은 트랜잭션에서 저장 |
| [ModelLog](model-log.md) | 기존 이력 저장·조회 구조의 참고 대상 |

[Dimension 목차](README.md)
