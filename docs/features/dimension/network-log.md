# NetworkLog

Network와 같은 트랜잭션에 변경 이력을 저장하고 목록·단건으로 조회하는 기능을 구현했다.

## 제공 기능

- [Network](network.md)의 생성·수정·삭제 이력을 대상별 목록과 로그 단건으로 조회한다.
- 진입점은 `/networks/{network_id}/logs`, `/network-logs/{log_id}`다. 구체 응답·오류·페이지네이션은 [API 계약](../../api-conventions.md#networknetworklog-http-계약)에서 관리한다.
- 삭제한 Network도 원래 UUID로 조회하며, 재등록한 새 UUID의 이력과 구분한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 실제 변경 | create/update/delete와 전체 id/name/code의 전·후 스냅샷 기록 | 사용자 합의 |
| 생성·삭제 스냅샷 | 생성 전·삭제 후는 null | 사용자 합의 |
| 부가 필드 | 로그 UUID·Network UUID·UTC 기록 시각·변경 요청 ID 기록 | 사용자 합의 |
| 동일 값 수정 | 로그를 추가하지 않음 | 사용자 합의 |
| 원자성 | Network 변경과 같은 세션·트랜잭션에서 커밋·롤백 | 사용자 합의 |
| 원본 삭제 | 이력 보존. 원본 UUID를 FK 없이 저장 | 사용자 합의에 따른 구현안 |
| 목록 | 기록 시각·로그 UUID 내림차순 | 사용자 합의 |
| 기록 없는 대상 | 정상 빈 이력 목록 반환 | 사용자 합의 |

로그는 추가 전용으로 DB UPDATE/DELETE도 방지한다. 자동 만료·행위자 필드는 기존 이력 구조처럼 추가하지 않기로 합의했다.

## 처리 흐름

1. Network 변경 유스케이스에서 전·후 스냅샷과 변경 요청 ID를 만들어 로그를 저장한다.
2. Network와 로그 저장 성공 후 명시적으로 commit한다. 실패 시 함께 rollback한다.
3. 조회는 원본 존재 확인 없이 로그 테이블을 조회한다. 목록 cursor는 해당 Network UUID에 묶는다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| `network_logs` | 추가·목록·단건 조회 | 작업·시각·요청·JSONB 전후 스냅샷 저장 |

- 변경 유스케이스에는 Network·NetworkLog UoW, 이력 조회에는 로그 저장소만 선언한 UoW Protocol을 사용한다.
- 로그는 Network에 FK를 두지 않아 물리 삭제 후에도 보존한다. 스냅샷 조건·작업 종류는 도메인과 DB 제약에서 검증한다.
- 현재 조회 요청 ID와 로그의 변경 당시 요청 ID를 구분하는 기존 계약을 유지하기로 합의했다.

## 조회와 인덱스

| 조회 | 조건·정렬 | 인덱스 | 역할 |
| --- | --- | --- | --- |
| 이력 단건 | 로그 UUID | PK(id) | 식별자 조회 |
| 대상별 이력 | network_id, occurred_at DESC, id DESC | (network_id, occurred_at, id) | 대상 필터·최신순 cursor 조회 |

- 동일 시각은 로그 UUID로 정렬한다. 정렬은 실제 commit 순서를 보장하지 않는다.
- 목록 종류·정렬·Network UUID를 cursor 서명 범위에 포함한다. 다른 대상·차원의 cursor는 거부한다.
- 실제 PostgreSQL에서 조회·동일 시각 경계·대상 분리를 검증했다. 대표 규모 실행 계획·인덱스 사용·성능은 미확인이다.

## 캐시

사용하지 않기로 합의했다. 키·TTL·무효화·장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치 | 역할·확인한 동작 |
| --- | --- | --- |
| 도메인·ORM | [NetworkLog](../../../src/mdm_demo/domain/entities/network_log.py), [ORM](../../../src/mdm_demo/infrastructure/persistence/models/network_log.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/network_log_mapper.py) | 불변 스냅샷·JSONB·DB 제약·왕복 |
| 유스케이스·조회 | [NetworkLogUseCases](../../../src/mdm_demo/application/use_cases/network_log.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/network_log_repository.py), [cursor](../../../src/mdm_demo/infrastructure/pagination/network_log_cursor.py) | 로그 전용 UoW 계약·최신순·대상 UUID 범위 |
| HTTP | [라우터](../../../src/mdm_demo/presentation/routers/network_log.py), [응답](../../../src/mdm_demo/presentation/schemas/network_log.py), [예제](../../../src/mdm_demo/presentation/schemas/network_examples.py) | 대상별 목록·단건·응답 스냅샷 |
| 로그 보호 | [마이그레이션](../../../migrations/versions/0006_network_dimension.py) | UPDATE/DELETE 방지 트리거·원본 FK 없음 |
| 검증 | [로그 단위](../../../tests/unit/application/test_network_log.py), [영속성](../../../tests/integration/persistence/test_network.py), [이력 API](../../../tests/api/test_network_log.py), [OpenAPI](../../../tests/api/test_network_openapi_examples.py) | 로그만 가진 UoW·원자성·취소·보존·no-op·동률 최신순·대상 cursor·실행 예제 |

- Scalar에서 생성·수정·삭제 후 원래 UUID로 이력을 조회하고 delete → update → create 순서 및 전후 스냅샷을 확인했다. no-op·실패한 중복 요청의 이력은 추가되지 않았다.
- 실제 이력 cursor를 복사해 다음 페이지와 로그 UUID 단건 요청을 실행했다. 조회 요청 ID와 변경 당시 요청 ID가 구분되며 첫 페이지의 cursor가 생성 코드·실제 요청 모두에서 생략된다.
- 전체 검사 결과는 [검수 결과](../../plans/issue-8-network-dimension.md#구현검수-결과), 실행 전제는 [README](../../../README.md), 원시 진입점은 [Makefile](../../../Makefile)를 따른다.
- 실제 commit 순서·순회 전체의 스냅샷 일관성·대표 규모 성능·commit 응답 유실 복구는 보장·검증하지 않는다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [Network](network.md) | 이력을 생성하는 독립 차원 |
| [CountryLog](country-log.md) | 추가 전용 이력 구조 참고 |

[Dimension 목차](README.md)
