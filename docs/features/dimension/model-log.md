# ModelLog

최신 main의 [CompanyLog](company-log.md)와 동일한 구조로 Model 이력 저장·조회를 구현했다. 공통 물리 로그 테이블 대신 전용 `model_logs`를 사용한다.

## 제공 기능

- Model 생성·수정·삭제 전후의 값을 보존하고 Model별 이력 목록·로그 단건을 조회한다.
- 진입점은 `/models/{model_id}/logs`, `/model-logs/{log_id}`다. 경로·응답·오류·정렬 계약은 [API 규약](../../api-conventions.md)을 따른다.
- 인증·행위자 저장, 통합 이력 검색은 이번 범위 밖이다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 생성 | 이전 값 없음 → 생성 값 | `ModelLog.record` |
| 수정 | 변경 전 값 → 변경 후 값 | `ModelLog.record` |
| 삭제 | 삭제 전 값 → 이후 값 없음 | `ModelLog.record` |
| 동일 값 수정 | 로그 생략 | `ModelUseCases.rename` |
| 스냅샷 | id/name/code 전체 값, Model 생성·수정 시각 제외 | `Model.snapshot` |
| 로그 변경 | 추가 전용, UPDATE·DELETE 거부 | Repository·DB 트리거 |
| 원본 삭제·코드 재사용 | 원래 UUID와 스냅샷 보존, 새 UUID의 이력과 분리 | FK 없는 대상 식별자 |

DB 관리자의 TRUNCATE·트리거 제거까지 차단하는 감사 보안 체계는 아니다. 자동 정리·보존 기한은 없으며 보존 정책 도입은 별도 합의가 필요하다.

## 처리 흐름

1. Model 유스케이스가 변경 전·후 스냅샷과 서버 발급 request ID를 전달한다.
2. `ModelLog.record`가 UUID 로그 ID·UTC 기록 시각을 부여하고 스냅샷을 복사·불변화한다.
3. Model 변경과 로그를 동일 UoW에서 함께 commit한다. 어느 하나라도 실패하면 함께 rollback한다.
4. 조회는 읽기 전용이며 현재 Model의 존재 여부를 검사하지 않는다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| `model_logs` | 추가·조회 | UUID 로그 ID, NOT NULL 대상 Model UUID, 작업 종류, UTC 기록 시각, request ID, 이전·이후 JSONB |
| `models` | 변경 유스케이스에서만 읽기·쓰기 | 변경과 이력의 원자성 |

- 전용 테이블이므로 dimension 구분 컬럼은 없다. 스냅샷 부재는 JSON null이 아닌 SQL NULL로 저장하며 작업별 조합을 CHECK로 검사한다.
- `model_id`는 FK 없이 보존한다. 원본 삭제 후에도 식별자와 스냅샷은 유지된다. 대상 존재를 DB의 FK로 보장하지 못하므로 유스케이스가 Model 변경과 이력을 같은 트랜잭션에서 저장한다.
- request ID는 서버 발급 요청 추적 값이며 사용자 식별자나 멱등성 키가 아니다. 행위자는 저장하지 않는다.
- 세션 종료·취소·commit 실패 정리는 공통 UoW를 따른다.

## 조회와 인덱스

| 조회 | 조건 | 관련 인덱스 | 역할 |
| --- | --- | --- | --- |
| Model별 목록 | model_id 및 occurred_at/id 경계 | (model_id, occurred_at, id) | 대상별 keyset 조회 |
| 로그 단건 | 로그 UUID | PK(id) | 단건 조회 |

- Model을 JOIN하거나 존재 검사하지 않으므로 삭제된 Model도 조회할 수 있다.
- cursor는 Model UUID·조회 종류·정렬에 묶는다. 다른 대상, Model 목록, Company 목록·이력 cursor를 거부한다.
- 시각·UUID 오름차순은 실제 commit 순서를 보장하지 않으며 페이지 순회의 스냅샷 일관성도 제공하지 않는다.
- 대표 규모에서의 실행 계획·성능은 미확인이다.

## 캐시

적용하지 않는다. PostgreSQL에 영속 저장·조회하므로 키·TTL·무효화·캐시 장애 정책은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치·심벌 | 역할·확인하는 동작 |
| --- | --- | --- |
| 도메인 | [ModelLog](../../../src/mdm_demo/domain/entities/model_log.py) | 작업별 스냅샷 검증·불변화 |
| 저장 | [모델](../../../src/mdm_demo/infrastructure/persistence/models/model_log.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/model_log_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/model_log_repository.py) | JSONB·SQL NULL·대상 식별 |
| 마이그레이션 | [0003](../../../migrations/versions/0003_model_dimension.py) | 전용 테이블·인덱스·추가 전용 트리거 |
| 조회 | [ModelLogUseCases](../../../src/mdm_demo/application/use_cases/model_log.py), [라우터](../../../src/mdm_demo/presentation/routers/model_log.py), [cursor](../../../src/mdm_demo/infrastructure/pagination/model_log_cursor.py) | 이력 목록·단건·cursor 대상 제한 |
| 검증 | [도메인](../../../tests/unit/domain/test_model.py), [유스케이스](../../../tests/unit/application/test_model_log.py), [영속성](../../../tests/integration/persistence/test_model.py), [API](../../../tests/api/test_model_log.py) | 불변 스냅샷·동일 값 생략·원자성·삭제 후 조회·코드 재사용 분리·cursor 경계 |

검증 진입점은 [Makefile](../../../Makefile)의 `make test-container`이며 전제는 [README](../../../README.md)를 따른다. 인증·성능·DB 관리자에 의한 변경 차단은 검증 대상이 아니다.

2026-10-11 전체 테스트 252개를 통과했고, Scalar에서 생성→수정→동일 값 수정→삭제 후 원래 UUID의 이력 목록을 조회해 create/update/delete 3건만 남는 것을 확인했다. 삭제 로그 단건에서 이전 스냅샷과 `after: null`도 확인했다.

## 관련 기능

- [Model](model.md)
- [CompanyLog](company-log.md)
- [Dimension 목차](README.md)

트랜잭션 조립은 [Model UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/model.py)를 사용한다. 차원과 로그 저장소는 같은 세션을 공유하고, 세션 정리·commit·rollback은 [공통 구현](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)에서 처리한다.

로그 조회 유스케이스는 [ModelLogUnitOfWork](../../../src/mdm_demo/application/ports/units_of_work/model.py)에 의존하며 로그 저장소만 요구한다. 실행 시 기존 차원별 SQLAlchemy UoW를 그대로 사용할 수 있다. 이는 의존하는 저장소의 범위를 좁히는 타입 계약이며 DB 읽기 전용 권한을 부여하는 장치는 아니다.
