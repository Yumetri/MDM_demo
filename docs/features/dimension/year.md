# Year

[이슈 #7](https://github.com/Yumetri/MDM_demo/issues/7)의 **구현한 기능**이다. 2026-10-12 사용자와 합의한 업무 규칙·HTTP 계약을 코드·마이그레이션·테스트에 반영했다.

## 제공 기능

- 제품 출시 연도를 독립 차원으로 등록·조회·수정·삭제한다.
- 다른 Dimension이나 제품·Model과 FK로 연결하지 않는다. 제품과의 연결은 해당 기능에서 별도로 설계한다.
- 진입점·필드·HTTP 오류·페이지네이션은 [API 규약의 Year 계약](../../api-conventions.md#yearyearlog-http-계약)을 따른다.
- 작업 순서·공통 변경 범위·검증은 [구현 계획](../../plans/issue-7-year-dimension.md)을 따른다.

## 업무 규칙과 제약

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 의미 | 제품 출시 연도 | 사용자 합의 |
| 연도 값 | 정수, 1900 이상 2999 이하. 미래 출시 예정 연도도 허용 | 사용자 합의 |
| 연도 유일성 | 같은 연도는 한 행만 등록. 생성·수정 모두 중복 금지 | 사용자 합의 |
| 코드 생성 | 연도의 십진수 문자열을 서버가 자동 생성. 직접 입력 금지 | 사용자 합의 |
| 수정 | UUID 유지. 연도 변경 시 코드도 함께 재생성 | 사용자 합의 |
| 같은 연도로 수정 | 성공하되 데이터·수정 시각·이력 변경 없음 | 사용자 합의 |
| 중복 연도로 수정 | 데이터 변경·이력 저장 모두 취소 | 사용자 합의 |
| 삭제·재등록 | 물리 삭제·이력 보존. 같은 연도 재등록 시 새 UUID | 사용자 합의 |
| 초기 데이터 | 자동 삽입 없이 필요한 연도만 등록 | 사용자 합의 |
| 운영 범위 | 인증·권한·행위자·멱등성 키·자동 재시도 제외 | 사용자 합의 |
| 목록 순서 | 연도 내림차순 | 사용자 합의 |
| 목록 크기 | Year·이력 모두 기본 20개, 허용 1~100개 | 사용자 합의 |
| 조회 범위 | 단건·고정 정렬 목록·대상별 이력. 검색·연도 범위 필터·총 개수 제외 | 사용자 합의 |
| 이력 | id/year/code 전후 값을 전용 YearLog에 추가 전용으로 저장 | 사용자 합의 |

코드 직접 입력을 허용하는 상위 이슈의 일반 원칙에 대한 Year 예외로 합의했다. 티켓에서는 이 기능 문서를 참조하고 상세 규칙을 복제하지 않는다. 기존 Company·Model·Brand의 코드 불변 정책은 Year에 적용하지 않는다.

## 처리 흐름

1. 도메인에서 연도의 타입·범위를 검증하고 코드를 생성한다.
2. 요청별 Year UoW를 열며 수정·삭제는 행 잠금 후 현재 값과 변경 전 스냅샷을 읽는다.
3. 도메인 메서드로 연도·코드를 함께 변경한다. 같은 값이면 쓰기·commit·로그 추가를 생략한다.
4. Year와 YearLog를 같은 세션에 저장하고 둘 다 성공한 뒤 명시적으로 commit한다.
5. 유일성 위반·로그 저장 실패·예외에는 함께 rollback한다. 취소·commit 실패의 세션 정리는 기존 공통 UoW를 재사용한다.

행 잠금·같은 세션의 전용 UoW·공통 정리 구현을 사용하며 실제 PostgreSQL 통합 테스트로 검증했다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| years | 조회·추가·수정·물리 삭제 | 내부 UUID, 출시 연도, 자동 코드, 생성·수정 시각 |
| year_logs | 추가·조회 | [YearLog](year-log.md)의 전후 스냅샷·요청 추적 |

- DB에 연도·코드 UNIQUE, 연도 범위 CHECK, 코드와 연도의 일치 CHECK를 둔다.
- 도메인·ORM·DTO는 각각 분리하고 Mapper로 변환한다.
- 동시 생성·서로 다른 행의 같은 연도 수정은 DB UNIQUE로 차단한다.
- 수정·삭제는 SELECT FOR UPDATE로 직렬 처리한다. 오래된 화면의 값을 별도로 거부하는 버전 검사는 추가하지 않는다.
- 변경·이력은 같은 UoW·트랜잭션에서 함께 commit/rollback한다.
- 마이그레이션은 기존 단일 head 뒤에 Year 전용 리비전을 추가한다. 기존 리비전·데이터는 보존한다.

## 조회와 인덱스

| 조회 | 필터·정렬 | 관련 인덱스 | 역할 |
| --- | --- | --- | --- |
| 단건·변경 대상 | UUID | PK(id) | 대상 조회·행 잠금 |
| 연도·코드 유일성 | 정수 연도·자동 코드 | UNIQUE(year), UNIQUE(code) | 동시 중복 방지 |
| 목록 | year DESC | UNIQUE(year)의 B-tree | 유일한 연도의 내림차순 keyset 조회 |

- Cursor에는 마지막 연도 경계와 Year 전용 조회·정렬 식별자를 포함한다.
- 다음 페이지는 마지막 연도보다 작은 값에서 조회한다. 경계 행 삭제 후에도 사용할 수 있어야 한다.
- 순회 중 연도 변경·재등록으로 항목이 이동할 수 있다. 스냅샷 일관성과 중복·누락 없는 순회는 보장하지 않는다.
- 실제 인덱스 사용·실행 계획·성능은 미확인이다. 인덱스 정의만으로 사용을 단정하지 않는다.
- 목록 크기·검색·연도 범위 필터·총 개수 제외와 cursor 계약은 사용자와 합의했다. 구체 HTTP 계약은 API 규약을 따른다.

## 캐시

캐시 없이 PostgreSQL에서 직접 조회하기로 합의했다. 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치 | 역할·검증 |
| --- | --- | --- |
| 도메인 | [Year](../../../src/mdm_demo/domain/entities/year.py), [YearValue](../../../src/mdm_demo/domain/value_objects/year_value.py), [YearCode](../../../src/mdm_demo/domain/value_objects/year_code.py) | 정수 범위·파생 코드·UUID 유지·같은 값 변경 생략 |
| 유스케이스·UoW | [YearUseCases](../../../src/mdm_demo/application/use_cases/year.py), [전용 UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/year.py) | 변경/이력 원자성·행 잠금·중복 변환 |
| 영속성 | [ORM](../../../src/mdm_demo/infrastructure/persistence/models/year.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/year_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/year_repository.py) | 타입 보존·UNIQUE/CHECK·내림차순 keyset |
| HTTP·조립 | [라우터](../../../src/mdm_demo/presentation/routers/year.py), [스키마](../../../src/mdm_demo/presentation/schemas/year.py), [예제](../../../src/mdm_demo/presentation/schemas/year_examples.py), [조립](../../../src/mdm_demo/composition/year.py) | strict 입력·공통 응답·명시적 등록 |
| 단위 검증 | [도메인](../../../tests/unit/domain/test_year.py), [유스케이스](../../../tests/unit/application/test_year.py), [cursor](../../../tests/unit/application/test_year_cursor.py) | 타입/범위·코드 일치·불변성·no-op·서명 경계 |
| 통합 검증 | [PostgreSQL](../../../tests/integration/persistence/test_year.py), [마이그레이션](../../../tests/integration/persistence/test_year_migration.py), [분기 통합](../../../tests/integration/persistence/test_dimension_merge_migration.py) | 동시 중복/행 잠금·함께 rollback·취소/commit 실패·기존 데이터 보존 |
| API 검증 | [CRUD](../../../tests/api/test_year.py), [OpenAPI 예제](../../../tests/api/test_year_openapi_examples.py), [전체/격리 조립](../../../tests/api/test_feature_composition.py) | 모든 본문 예제 실행·오류·페이지 경계·raw 2024.0 거부 |

실행 결과와 Scalar 브라우저 검수는 [검증 보고](../../reports/issue-7-validation.md)에 기록했다. 인덱스 실행 계획·대량 데이터 성능은 미확인이다.

검증 진입점은 [Makefile](../../../Makefile), 실행 전제는 [README](../../../README.md)를 따른다.

## 관련 기능

| 기능 | 관계 |
| --- | --- |
| [YearLog](year-log.md) | 변경과 같은 트랜잭션으로 저장하는 전용 이력 |
| [Model](model.md) | 독립된 제품 모델 차원. 이번 작업에서 FK 연결하지 않음 |
| [Company](company.md)·[Brand](brand.md)·[Country](country.md) | 기존 구조·검증의 참고 대상. 업무 규칙은 자동 적용하지 않음 |

[Dimension 목차](README.md)
