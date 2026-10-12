# Memory

저장공간 용량 Dimension의 CRUD와 변경 이력을 구현했다. [이슈 #9](https://github.com/Yumetri/MDM_demo/issues/9), [공통 원칙](https://github.com/Yumetri/MDM_demo/issues/1), [확정 구현 계획](../../plans/issue-9-memory.md)을 따른다.

## 제공 기능

- 숫자 용량과 단위를 분리해 관리하고 코드는 항상 자동 생성한다. Company·Model 등을 직접 참조하지 않는 독립 차원이며 제품 조합은 향후 Fact에서 연결한다.
- CRUD 진입점은 /memories, 이력은 [MemoryLog](memory-log.md)에서 제공한다. 필드·오류·HTTP 상태·페이지네이션 계약은 [API 규약](../../api-conventions.md#memorymemorylog-http-계약)에서 관리한다.
- PostgreSQL에서 직접 조회한다. 인증·권한·캐시·검색·필터·사용자 지정 정렬은 범위 밖이다.

## 업무 규칙과 제약

| 조건 | 규칙 | 구현 근거 |
| --- | --- | --- |
| 용량 | 1~2,147,483,647의 엄격한 JSON 정수. 0·음수·소수·문자열·실수·불리언 거부 | MemorySize·요청 스키마 |
| 단위 | 양끝 공백 제거·대문자 변환 후 GB·TB만 허용. 내부 공백·빈 값 거부 | MemorySize |
| 환산 | 1TB = 1000GB. 다른 항목의 같은 환산 용량 등록·수정 금지 | 도메인 계산·DB 생성 컬럼·UNIQUE |
| 코드 | 직접 입력 없음. 용량 숫자+정규화한 단위로 생성 | MemorySize.code |
| 수정 | 용량·단위 모두 필수. UUID·생성 시각 유지, 코드 자동 갱신 | Memory.change_size |
| 같은 환산 용량의 표기 변경 | 자기 항목의 1TB→1000GB 허용, 시각·이력 갱신 | Entity·유스케이스 |
| 동일 값 수정 | 정규화 후 용량·단위가 모두 같으면 성공, 데이터·시각·이력 유지 | 유스케이스의 저장·commit 생략 |
| 삭제·재등록 | 물리 삭제·이력 보존. 같은 용량 재등록은 새 UUID | 삭제·생성 유스케이스 |
| 차원 관계 | 다른 차원의 FK 없음 | ORM·마이그레이션 |

코드 예시는 256GB·1TB다. 상위 이슈의 선택적 코드 입력보다 Memory에 대한 사용자 합의를 우선하며 직접 입력을 제공하지 않는다.

## 처리 흐름

1. 불변 MemorySize VO가 검증·정규화·코드·환산 용량 계산을 수행한다.
2. 생성 시 데이터 저장·flush 후 생성 로그를 같은 UoW에 추가한다.
3. 수정·삭제는 행 잠금 후 최신 값의 스냅샷을 읽고 Entity 메서드로 변경한다.
4. 표기 변경도 실제 변경으로 저장하며, 동일 값 수정은 저장·로그·commit을 생략한다.
5. 변경과 로그 저장이 성공하면 명시적으로 commit한다. 실패·미커밋 종료·취소·commit 실패는 공통 UoW가 rollback·세션 정리를 수행한다.

## 데이터와 트랜잭션

| 테이블 | 용도 |
| --- | --- |
| memories | UUID PK, 입력 용량·정규화 단위, 파생 코드, DB 생성 GB 환산값, UTC 생성·수정 시각 |
| memory_logs | FK 없는 원본 UUID와 변경 전후 스냅샷 |

- capacity는 INTEGER, capacity_gb는 BIGINT 생성 컬럼이다. 곱셈 전에 bigint로 변환해 최대 TB 입력의 중간 계산 넘침을 방지한다. HTTP 응답은 입력 용량·정규화한 단위를 보존한다.
- 코드·환산 용량 UNIQUE와 용량 범위·단위·파생 코드 일치 CHECK를 둔다. 알려진 용량·코드 UNIQUE 위반만 중복으로 변환하며 다른 DB 오류를 중복으로 오인하지 않는다.
- 수정·삭제는 SELECT FOR UPDATE로 직렬 처리한다. 같은 항목의 연속 수정은 나중 처리된 값이 최종 값이며 낙관적 버전 검사는 제공하지 않는다.
- 데이터와 로그는 같은 세션·UoW에서 함께 commit/rollback한다. commit 응답 유실의 결과 확정·자동 재시도는 제공하지 않는다.
- Memory 전용 마이그레이션의 downgrade는 Memory 데이터·이력을 제거하며 기존 차원은 보존한다.

## 조회와 인덱스

| 조회 | 인덱스 | 역할 |
| --- | --- | --- |
| 단건·수정·삭제 | PK(id) | 대상 검색·행 잠금 |
| 코드 유일성 | UNIQUE(code) | 자동 코드 중복 방지 |
| 환산 용량 유일성 | UNIQUE(capacity_gb) | GB/TB 동치 중복 방지 |
| 목록 | (created_at, id) | 고정 오름차순 keyset 경계 |

cursor·목록의 일관성 범위는 API 규약을 따른다. 수정으로 정렬 위치는 바뀌지 않는다. 쿼리 동작은 실제 PostgreSQL에서 확인했으나 대표 규모 데이터의 EXPLAIN·성능 측정은 미확인이다.

## 캐시

사용하지 않는다. PostgreSQL 직접 조회이므로 캐시 키·TTL·무효화·장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 근거 |
| --- | --- |
| 도메인 | [Memory](../../../src/mdm_demo/domain/entities/memory.py), [MemorySize](../../../src/mdm_demo/domain/value_objects/memory_size.py) |
| 유스케이스 | [MemoryUseCases](../../../src/mdm_demo/application/use_cases/memory.py) |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/memory.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/memory_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/memory_repository.py) |
| 트랜잭션·조립 | [차원 UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/memory.py), [공통 UoW](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py), [조립](../../../src/mdm_demo/composition/memory.py) |
| HTTP·예제 | [라우터](../../../src/mdm_demo/presentation/routers/memory.py), [요청·응답](../../../src/mdm_demo/presentation/schemas/memory.py), [예제](../../../src/mdm_demo/presentation/schemas/memory_examples.py) |
| 스키마 | [마이그레이션](../../../migrations/versions/0006_memory_dimension.py) |
| 단위 | [도메인](../../../tests/unit/domain/test_memory.py), [유스케이스](../../../tests/unit/application/test_memory.py), [cursor](../../../tests/unit/application/test_memory_cursor.py) |
| 실제 DB | [제약·원자성·동시성·정리](../../../tests/integration/persistence/test_memory.py), [마이그레이션 보존·왕복](../../../tests/integration/persistence/test_memory_migration.py) |
| API | [CRUD·오류](../../../tests/api/test_memory.py), [OpenAPI 예제 실행](../../../tests/api/test_memory_openapi_examples.py) |

2026-10-12 make check(진단 0), Memory 구현 당시 make test-unit(315개), 격리 Compose의 make test-container(1160개)를 통과했다. Year(PR #19)가 포함된 최신 main을 반영했다. 빈 DB·각 기존 차원 head에서 업그레이드, 기존 데이터/로그 보존·ORM 일치·최종 단일 head를 확인했다. 0007_merge_year_memory로 Year·Memory head를 연결하고 각각/동시 적용 DB의 데이터·로그 보존과 merge-only downgrade/재적용도 확인했다. make compose-check·make up·make smoke도 통과했다.

실제 Scalar에서 정상 생성·단위 정규화·최대 TB, 중복·불리언·코드 입력 오류, 용량 수정·표기 변경·동일 값 수정, 삭제 후 404·이력 보존·재등록 UUID 분리, 로그 단건·실제 cursor 다음 페이지·cursor 오류를 확인했다. 첫 페이지는 생성 코드와 실제 서버 요청 모두 cursor를 생략했다. Scalar가 정수형 실수 256.0을 256으로 직렬화하는 결함은 사용자 승인 후 실패 예제를 256.5로 교체해 해결했다. POST·PATCH 예제의 실제 전송 본문과 422 VALIDATION_ERROR, 데이터·시각·이력 불변을 다시 확인했다. 원시 JSON 256.0 거부는 별도 API 테스트 2개로 보존하며 문서 상단의 원시 HTTP 안내를 따른다.

검증 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다. 인증·성능·실네트워크 commit 응답 유실 복구는 검증 범위 밖이다.

## 관련 기능

- [MemoryLog](memory-log.md)
- [Dimension 목차](README.md)


### main 충돌 해결 후 통합

Category·Network가 포함된 main을 반영하고 [0009 병합](../../../migrations/versions/0009_merge_memory_dimensions.py)으로 최신 단일 head를 구성했다. 기존 Memory·Year·Category·Network 리비전의 ID·부모·내용은 유지한다. [통합 보존 검사](../../../tests/integration/persistence/test_memory_main_merge_migration.py)는 10개 초기 상태에서 8개 차원의 데이터·이력 보존, merge-only downgrade·재적용을 확인한다. 최종 전체 테스트 1160개·정적 검사·make up·make smoke를 통과했다. 새 Scalar에서 모든 차원과 안내가 표시되고 Memory 첫 페이지의 생성 코드·실제 요청은 cursor 없이 200을 반환한다.
