# MemoryLog

Memory 변경 전후 기록과 조회를 구현했다. [Memory](memory.md)의 변경과 같은 UoW에서 저장하며 [확정 구현 계획](../../plans/issue-9-memory.md)을 따른다.

## 제공 기능

- 대상별 이력 목록·로그 단건을 조회한다. 삭제된 Memory의 기록도 원래 UUID로 조회하며 기록 없는 대상 목록은 성공·빈 배열이다.
- 구체 필드·경로·상태·오류·페이지네이션은 [API 규약](../../api-conventions.md#memorymemorylog-http-계약)에서 관리한다.
- 로그 수정·삭제 API, 행위자·자동 만료·캐시는 제공하지 않는다.

## 업무 규칙과 제약

| 조건 | 규칙 | 근거 |
| --- | --- | --- |
| 생성 | 이전 없음 → 생성 값 | MemoryLog.record |
| 수정·표기 변경 | 이전 값 → 변경 후 값. 1TB→1000GB도 기록 | 유스케이스 |
| 동일 값 수정 | 새 로그 없음 | 유스케이스 |
| 삭제 | 삭제 전 값 → 이후 없음, 기록 보존 | 유스케이스·FK 없는 테이블 |
| 스냅샷 | id·capacity·unit·code. 숫자 용량은 정수로 보존 | 도메인·Mapper·DTO·응답 스키마 |
| 원자성 | Memory 변경과 같은 세션·UoW·DB 트랜잭션 | 차원 UoW |
| 추가 전용 | 기존 로그 UPDATE/DELETE 거부 | DB 트리거 |

로그 UUID, 원본 Memory UUID, 작업, UTC 기록 시각, 변경 당시 서버 request ID를 저장한다. 현재 조회 요청 ID와 변경 당시 요청 ID는 구분한다.

## 처리 흐름

1. Memory 유스케이스가 변경 전후 스냅샷을 만든다.
2. MemoryLog가 스냅샷을 복사·불변화하고 작업별 전후 값 조합을 검증한다.
3. 데이터와 로그 저장이 모두 성공하면 명시적으로 commit하며 하나라도 실패하면 함께 rollback한다.
4. 읽기 전용 유스케이스는 로그 저장소만 선언한 UoW Protocol에 의존한다.

## 데이터와 트랜잭션

memory_logs 전용 테이블에 원본 UUID를 FK 없이 저장한다. before/after는 JSONB이며 용량을 문자열로 바꾸지 않는다. 작업별 NULL 조합 CHECK와 UPDATE/DELETE 거부 트리거를 둔다. 공통 UoW가 예외·취소·commit 실패·미커밋 종료의 정리를 처리한다.

## 조회와 인덱스

| 조회 | 인덱스 | 역할 |
| --- | --- | --- |
| 대상별 목록 | (memory_id, occurred_at, id) | 대상 필터·기록 시각/로그 UUID 오름차순 keyset 경계 |
| 단건 | PK(id) | 로그 식별자 조회 |

현재 Memory 존재를 먼저 검사하지 않는다. 이력 cursor는 대상 UUID까지 서명 문맥에 묶고 다른 차원·목록·대상의 토큰은 거부한다. 실제 DB 조회·삭제 후 이력·서명 페이지 순회를 검증했으며 EXPLAIN·대표 규모 성능은 미확인이다.

## 캐시

사용하지 않는다. DB 직접 조회이므로 키·TTL·무효화·fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 근거 |
| --- | --- |
| 도메인·유스케이스 | [MemoryLog](../../../src/mdm_demo/domain/entities/memory_log.py), [조회](../../../src/mdm_demo/application/use_cases/memory_log.py) |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/memory_log.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/memory_log_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/memory_log_repository.py) |
| HTTP | [라우터](../../../src/mdm_demo/presentation/routers/memory_log.py), [스키마](../../../src/mdm_demo/presentation/schemas/memory_log.py) |
| 단위 | [로그 전용 UoW·cursor](../../../tests/unit/application/test_memory_log.py), [스냅샷 불변성](../../../tests/unit/domain/test_memory.py) |
| 실제 DB·API | [영속성](../../../tests/integration/persistence/test_memory.py), [이력 조회](../../../tests/api/test_memory_log.py), [OpenAPI 예제](../../../tests/api/test_memory_openapi_examples.py) |

2026-10-12 전체 테스트 1160개에서 스냅샷 정수 타입·Mapper 왕복, 로그 실패의 원자성·취소/commit 실패 정리, 추가 전용 보호, 삭제 후 목록·없는 로그·cursor 교차 거부를 검증했다. Scalar에서 표기 변경 전후 값·로그 단건, 동일 값 수정 시 이력 미증가, 삭제 후 원래 UUID의 create/update/delete 이력을 확인했다. 검증 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다.

## 관련 기능

- [Memory](memory.md)
- [Dimension 목차](README.md)
