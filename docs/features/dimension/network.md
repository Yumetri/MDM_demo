# Network

사용자와 합의한 Network CRUD·NetworkLog를 구현했다. 아래는 현재 구현과 검증 범위다.
작업은 [이슈 #8](https://github.com/Yumetri/MDM_demo/issues/8), 공통 원칙은 [이슈 #1](https://github.com/Yumetri/MDM_demo/issues/1)을 따른다.

## 제공 기능

- 제품이 지원하는 이동통신 규격을 관리하는 독립 Dimension이다. 한 행은 `3G`, `LTE`, `5G`처럼 규격 하나를 표현한다. 지원 규격 조합·통신사·제품 연결은 다루지 않는다.
- 규격명·고유코드를 등록·조회·수정·삭제하며 이력은 [NetworkLog](network-log.md)에서 조회한다.
- 진입점은 `/networks`, `/networks/{network_id}`다. API의 구체 필드·상태·오류·페이지네이션은 [API 계약](../../api-conventions.md#networknetworklog-http-계약)에서 관리한다. Network·NetworkLog의 요청·응답과 실행 예제를 OpenAPI·Scalar에 제공한다.
- 인증·권한·캐시는 범위 밖이며 PostgreSQL에서 직접 조회한다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 업무 필드 | `name`, `code`만 관리. UUID·생성/수정 시각은 시스템 필드 | 사용자 합의 |
| 규격 등록 | 자유 등록. 실제 통신 표준 존재 여부는 검사하지 않음 | 사용자 합의 |
| 이름 정규화 | 양끝 공백 제거 → 대문자 변환 → NFC 정규화 | 사용자 합의 |
| 이름 길이·문자 | 정규화 후 1~100자. 내부 공백·한글·숫자·기호 보존. 빈 이름·공백만 있는 이름 거부 | 사용자 합의 |
| 이름 유일성 | 정규화 후 동일한 이름의 생성·수정 금지. DB UNIQUE로 동시 요청도 차단 | 사용자 합의 |
| 직접 코드 | 양끝 공백 제거 후 ASCII 영문·숫자 1~20자. 대문자 저장. 내부 공백·기호 금지 | 사용자 합의 |
| 코드 생략 | 정규화한 이름의 ASCII 영문·숫자를 모두 추출해 대문자로 생성 | 사용자 합의 |
| 자동 생성 실패 | 추출 결과가 없거나 20자 초과·코드 중복이면 실패. 임의 절단·접미사·재생성 없음. 직접 입력 요구 | 사용자 합의 |
| 코드 유일성 | Network 테이블 내 UNIQUE | 상위 이슈·사용자 합의 |
| 수정 | 이름만 수정. 코드 불변이며 이름을 바꿔도 유지 | 사용자 합의 |
| 동일 값 수정 | 정규화 후 이름이 같으면 성공하되 데이터·수정 시각·로그 유지 | 사용자 합의 |
| 삭제·재등록 | 물리 삭제·이력 보존. 삭제한 이름·코드 재사용 가능. 재등록 시 새 UUID 발급 | 사용자 합의 |
| 동시 수정·삭제 | 행 잠금으로 최신 값을 읽어 순서대로 처리. 나중에 성공한 수정이 최종 값. 별도 버전 검사 없음 | 사용자 합의 |
| 초기 데이터 | 자동 삽입 없이 빈 테이블에서 API로 등록 | 사용자 합의 |

예: ` lte ` → 이름 `LTE`, 자동 코드 `LTE`. `5G NR` → 코드 `5GNR`, `LTE-A` → 코드 `LTEA`. 서로 다른 이름이 같은 자동 코드를 만들면 직접 코드가 필요하다.
PostgreSQL에 저장할 수 없는 NUL·UTF-8로 표현할 수 없는 단독 surrogate는 기존 차원과 같은 입력 정책으로 거부하기로 합의했다.

## 처리 흐름

1. 생성 입력을 도메인 VO에서 검증·정규화하고 코드가 생략됐으면 생성한다.
2. 요청마다 Network UoW·세션을 만든다. 생성은 저장·flush에서 유일성을 검사한다.
3. 수정·삭제는 행 잠금 획득 후 현재 값을 읽고 변경 전 스냅샷을 만든다. 변경은 Root 메서드를 거친다.
4. 동일 값 수정은 저장·로그·commit 없이 현재 값을 반환한다.
5. 실제 변경과 NetworkLog를 같은 세션에 저장한 후 명시적으로 commit한다. 실패·미커밋 종료에는 rollback하고 취소·commit 실패에도 세션을 정리한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| `networks` | 생성·조회·이름 수정·물리 삭제 | 규격 데이터와 시스템 필드 |
| `network_logs` | 추가·조회 | 변경 전·후 이력 보존 |

- Network는 다른 차원의 FK를 두지 않는다. Network 변경과 로그 추가는 하나의 UoW·DB 트랜잭션에서 함께 성공·실패한다.
- 정규화 이름·코드에 각각 UNIQUE를 둔다. 이름은 저장 값 자체를 비교하는 C collation을 사용한다. 정규화는 도메인 책임이며 DB 직접 쓰기의 NFC·대문자 변환까지 보장하지 않는다.
- 형식·길이·로그 스냅샷 조건은 DB 제약도 둔다. 알려진 UNIQUE 제약 위반만 해당 중복 오류로 변환한다.
- UUID v4·UTC 시각, 자동 재시도·멱등성 키 없음은 기존 공통 정책을 유지하기로 합의했다. commit 응답 유실의 결과 확정 기능은 포함하지 않는다.

## 조회와 인덱스

| 조회 | 필터·정렬 | 인덱스 | 역할 |
| --- | --- | --- | --- |
| 단건·수정·삭제 | Network UUID | PK(id) | 식별자 조회·행 잠금 |
| 이름·코드 유일성 | 정규화된 값 | UNIQUE(name), UNIQUE(code) | 동시 요청 중복 방지 |
| 목록 | 생성 시각·UUID 내림차순 | (created_at, id) | 최신 등록부터 keyset 조회 |

- 최신순·목록 범위는 사용자와 합의했다. cursor는 전체 정렬 키로 경계를 계산하며 다음 페이지는 이전 마지막 행보다 작은 키를 조회한다. 이름 수정은 정렬 위치를 바꾸지 않는다.
- Network 전용 조회·정렬 식별자를 사용하며 이력 cursor와 구분한다. 상세 계약은 API 규약을 따른다.
- 실제 PostgreSQL에서 쿼리·경계 동작을 검증했다. 대표 규모 데이터의 실행 계획·성능·실제 인덱스 사용은 미확인이다.

## 캐시

사용하지 않기로 합의했다. PostgreSQL에서 직접 조회하며 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치 | 역할·확인한 동작 |
| --- | --- | --- |
| 도메인 | [Network](../../../src/mdm_demo/domain/entities/network.py), [NetworkName](../../../src/mdm_demo/domain/value_objects/network_name.py), [NetworkCode](../../../src/mdm_demo/domain/value_objects/network_code.py) | Root 변경·정규화·유일 코드 생성·불변 코드 |
| 유스케이스 | [NetworkUseCases](../../../src/mdm_demo/application/use_cases/network.py), [UoW Protocol](../../../src/mdm_demo/application/ports/units_of_work/network.py) | 원자적 변경·로그·no-op·오류 변환 |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/network.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/network_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/network_repository.py) | DB 제약·왕복·행 잠금·최신순 조회 |
| 조립·트랜잭션 | [Network 조립](../../../src/mdm_demo/composition/network.py), [Network UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/network.py), [공통 UoW](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py) | 차원 저장소와 로그 저장소의 세션 공유·자원 정리 |
| HTTP·예제 | [라우터](../../../src/mdm_demo/presentation/routers/network.py), [스키마](../../../src/mdm_demo/presentation/schemas/network.py), [예제](../../../src/mdm_demo/presentation/schemas/network_examples.py) | API 계약·성공/실패/경계값 실행 예제 |
| cursor·스키마 | [Network cursor](../../../src/mdm_demo/infrastructure/pagination/network_cursor.py), [마이그레이션](../../../migrations/versions/0006_network_dimension.py) | 내림차순 서명 범위·제약·인덱스·이력 보호 |

- [도메인 검사](../../../tests/unit/domain/test_network.py): 이름 정규화·정준 동등성·대문자 확장 길이, 코드 1/20자·전체 추출·불가 조건, 불변 코드·Entity 동등성·no-op·스냅샷.
- [유스케이스](../../../tests/unit/application/test_network.py)·[cursor 검사](../../../tests/unit/application/test_network_cursor.py): 중복·자동 코드 오류 구분, commit·로그 생략, 토큰 형식·서명·조회 범위·키 교체.
- [실제 PostgreSQL 검사](../../../tests/integration/persistence/test_network.py): Mapper 왕복, DB 형식·유일성·동시성, 로그 저장/commit 실패·취소·정리, 최신순 동일 시각 UUID 경계·경계 행 삭제.
- [마이그레이션](../../../tests/integration/persistence/test_network_migration.py)·[기존 병렬 head 경로](../../../tests/integration/persistence/test_dimension_merge_migration.py): 단일 head, 빈 DB·기존 Brand/Country 양쪽 경로·공통 head 업그레이드, 네 차원 데이터·이력 보존, Network downgrade·재적용 및 ORM 일치.
- [API 검사](../../../tests/api/test_network.py)·[OpenAPI 예제 실행](../../../tests/api/test_network_openapi_examples.py): 실제 요청·응답·없음/null/빈 값·중복·다른 네 차원 cursor 거부·최신순 페이지·예제·응답 모델·공통 안내.
- Scalar에서 생성·409 충돌·422 null·최신순 첫/다음 페이지·400 cursor·동일 값 수정·실제 이름 수정·이름 중복·삭제·삭제 후 이력·로그 단건을 실행했다. 첫 페이지 생성 코드와 실제 서버 요청 기록에서 cursor 생략을 확인했다.
- 전체 검사 결과·검수 환경은 [작업 계획의 검수 결과](../../plans/issue-8-network-dimension.md#구현검수-결과)를 따른다. 검사 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)다.
- 대표 규모 성능·실네트워크 commit 응답 유실 복구는 검증 범위 밖이다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [NetworkLog](network-log.md) | 변경과 함께 저장하며 삭제 후에도 보존하는 이력 |
| [Country](country.md), [Model](model.md) | 구조 참고. 각 차원의 개별 정책은 Network에 자동 적용하지 않음 |

[Dimension 목차](README.md)


### 최신 main 통합 검증 범위

2026-10-12 검수 중 Year 티켓 #7이 main에 병합되어 기준을 `c1f94f6d8f2738cf20a5d29b33b00ef0ed634bf0`으로 갱신했다. 기존 Network·Year 리비전은 그대로 유지하고 [병합 리비전](../../../migrations/versions/0007_merge_network_year.py)이 두 경로를 단일 head로 연결한다. [통합 마이그레이션 검사](../../../tests/integration/persistence/test_network_year_merge_migration.py)는 빈 DB·Network head·Year head·양쪽 head에서 최신 head로 업그레이드할 때 데이터와 로그를 보존하고 반복 적용을 검증한다.


### Category 병합 후 최신 head

사용자가 Category PR #20과의 추가 통합을 승인해 기준은 `c5cea8aacd8a1cced8cdf10a6ce72983a50da8d6`이다. 앞 절의 Network·Year 병합 리비전은 그대로 보존하며 [빈 최종 병합](../../../migrations/versions/0008_merge_dimension_heads.py)이 Category·Year 병합 경로와 합친다. [통합 보존 검사](../../../tests/integration/persistence/test_network_year_merge_migration.py)는 8개 초기 상태에서 세 차원의 데이터·로그 보존과 반복 적용을 확인한다.
