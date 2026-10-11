# Brand

제품 브랜드를 나타내는 독립 Dimension의 CRUD를 구현했다. 작업은 [이슈 #4](https://github.com/Yumetri/MDM_demo/issues/4), 공통 원칙은 [이슈 #1](https://github.com/Yumetri/MDM_demo/issues/1)을 따른다.

## 제공 기능

- 브랜드명과 고유코드를 등록·조회·수정·삭제한다. 브랜드 예시는 `Galaxy`, `Redmi`다.
- 스타 스키마의 독립 차원으로 Company·Model을 참조하지 않는다. 차원 조합은 추후 Fact에서 처리하며 Fact는 이번 구현 범위 밖이다.
- 진입점은 `/brands` 및 `/brands/{brand_id}`다. 요청·응답·오류·페이지네이션 계약은 [API 규약](../../api-conventions.md)을 따른다.
- 로컬 개발용 기능이다. 인증·권한, 검색·선택 정렬·캐시는 범위 밖이며, 이력 조회는 [BrandLog](brand-log.md)에서 제공한다.

## 업무 규칙과 제약

아래 규칙은 사용자와 합의했으며 도메인과 DB·API에 반영했다.

| 조건 | 적용되는 규칙·결과 | 근거 |
| --- | --- | --- |
| 브랜드명 | 양끝 공백 제거 후 1~100자, 내부 공백 보존, 중복 허용 | `BrandName` |
| 직접 코드 | 양끝 공백 제거 후 ASCII 영문·숫자 정확히 3자, 대문자로 정규화 | `BrandCode` |
| 코드 자동 생성 | 브랜드명에서 ASCII 영문·숫자만 남긴 뒤 앞 3자를 대문자로 변환 | `BrandCode.from_name` |
| 자동 생성 실패 | 추출 결과 3자 미만 또는 코드 중복이면 오류. 다른 코드로 재생성하지 않음 | 도메인·유스케이스 |
| 코드 유일성 | Brand 테이블 내 유일함. 정규화 후 값을 비교 | `uq_brands_code` |
| 수정 | 코드 변경 금지, 브랜드명만 변경. 이름 변경 후에도 기존 코드 유지 | `Brand.rename`·수정 스키마 |
| 동일 값 수정 | 정규화된 이름이 같으면 성공, 데이터·수정 시각·이력 변경 없음 | `Brand.rename`·유스케이스 |
| 삭제 | 물리 삭제, 이력 보존. 삭제 코드 재사용 시 새 UUID 부여 | 삭제·등록 유스케이스 |
| 변경 이력 | 변경 전·후 전체 id/name/code 스냅샷을 변경과 함께 저장 | `BrandLog`·동일 UoW |

자동 생성 예: `Galaxy` → `GAL`, `Redmi` → `RED`, `갤럭시 S24` → `S24`, `123` → `123`. `가나다 AB`는 실패한다. 직접 입력한 ` s24 `는 `S24`로 저장하며 내부 공백은 허용하지 않는다.

코드의 생략·null·빈 값 처리 등 HTTP 계약은 API 규약에서 관리한다. 이름의 NUL과 UTF-8로 표현할 수 없는 단독 surrogate는 Company와 같이 거부하며, 정상 한글·이모지는 보존한다.

## 처리 흐름

1. 도메인이 브랜드명·코드를 검증하고 정규화하거나 자동 생성한다.
2. 요청마다 새 UoW·세션을 열어 등록을 수행하고 flush에서 코드 유일성을 검사한다.
3. 수정·삭제는 행 잠금 획득 후 최신 값을 읽어 변경 전 스냅샷을 만든다.
4. 도메인 메서드를 통해 변경하고 Brand·BrandLog를 같은 세션에 저장한다.
5. 두 저장이 성공하면 명시적으로 commit한다. 조회와 변경 없는 수정은 commit하지 않고 정리한다.

## 데이터와 트랜잭션

| 대상 | 읽기·쓰기 | 용도 |
| --- | --- | --- |
| `brands` | 조회·생성·수정·삭제 | UUID v4 PK, 브랜드명, 코드, UTC 생성·수정 시각 |
| `brand_logs` | 추가·조회 | [BrandLog](brand-log.md)의 변경 이력 |

- 브랜드명 길이·일반 양끝 공백, 코드 형식·UNIQUE는 DB에서도 검증한다. 유니코드 양끝 공백 정규화는 도메인이 담당한다.
- Company·Model이나 다른 Dimension의 FK는 없다. 내부 식별자는 코드 재사용과 무관하게 새로 발급한다.
- 변경과 로그는 같은 UoW·DB 트랜잭션에서 함께 commit/rollback한다. 로그 실패·commit 실패·취소 때에도 세션을 정리한다.
- 동시 수정·삭제는 `SELECT … FOR UPDATE`로 직렬 처리한다. 나중에 처리된 수정이 최종 값이며 오래된 클라이언트 값을 별도로 거부하지 않는다.
- 알려진 코드 UNIQUE 위반만 중복으로 변환한다. commit 응답 유실 시 결과 확정·자동 재시도는 제공하지 않는다.
- [0004 마이그레이션](../../../migrations/versions/0004_brand_dimension.py)은 Brand 전용 테이블·인덱스·트리거만 추가한다. 기존 Company·Model 마이그레이션은 보존한다. [병합 리비전](../../../migrations/versions/0005_merge_brand_country.py)은 Brand `0004`와 Country `0004_country`를 하나의 head로 연결한다. 다운그레이드는 Brand 데이터·이력을 제거하므로 보존이 필요하면 먼저 백업해야 한다.

## 조회와 인덱스

| 조회 | 조건 | 관련 인덱스 | 역할 |
| --- | --- | --- | --- |
| 단건·수정·삭제 | UUID | PK(id) | 대상 조회·행 잠금 |
| 코드 유일성 | 정규화한 코드 | UNIQUE(code) | 동시 등록 중복 방지 |
| 목록 | 생성 시각·UUID 오름차순 | (created_at, id) | keyset 페이지 경계 조회 |

- 목록 크기·cursor 계약은 API 규약을 따른다. 이름 변경은 정렬 위치를 바꾸지 않는다.
- Company·이력 목록의 cursor는 Brand 목록에서 거부한다. 경계 행이 삭제돼도 다음 페이지를 조회할 수 있다.
- 대표 규모 데이터의 EXPLAIN·성능은 미확인이다. 인덱스 정의만으로 실제 사용을 단정하지 않는다.

## 캐시

적용하지 않는다. PostgreSQL에서 직접 조회하므로 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다.

## 구현과 검증

| 구분 | 위치·심벌 | 역할·확인하는 동작 |
| --- | --- | --- |
| 도메인 | [Brand](../../../src/mdm_demo/domain/entities/brand.py), [BrandName](../../../src/mdm_demo/domain/value_objects/brand_name.py), [BrandCode](../../../src/mdm_demo/domain/value_objects/brand_code.py) | 정규화·자동 생성·불변 코드·수정 |
| 유스케이스 | [BrandUseCases](../../../src/mdm_demo/application/use_cases/brand.py) | UoW·로그·오류 변환 |
| 영속성 | [브랜드](../../../src/mdm_demo/infrastructure/persistence/models/brand.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/brand_mapper.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/brand_repository.py) | 손실 없는 변환·잠금·유일성 |
| HTTP | [라우터](../../../src/mdm_demo/presentation/routers/brand.py), [스키마](../../../src/mdm_demo/presentation/schemas/brand.py), [예제](../../../src/mdm_demo/presentation/schemas/brand_examples.py) | 요청·응답·Scalar 실행 예제 |
| 단위 검증 | [도메인](../../../tests/unit/domain/test_brand.py), [유스케이스](../../../tests/unit/application/test_brand.py), [cursor](../../../tests/unit/application/test_brand_cursor.py) | 경계값·동일 값 수정·오류·서명 |
| 통합 검증 | [영속성](../../../tests/integration/persistence/test_brand.py), [마이그레이션](../../../tests/integration/persistence/test_brand_migration.py) | Mapper 왕복·원자성·동시 변경·commit 실패·취소·추가 전용 로그 |
| API 검증 | [API](../../../tests/api/test_brand.py), [OpenAPI 예제](../../../tests/api/test_brand_openapi_examples.py) | CRUD·코드 재사용·오류·페이지 경계·예제 실행 |

검증 진입점은 [Makefile](../../../Makefile)의 `make check`, `make test-container`, `make smoke`이며 실행 전제는 [README](../../../README.md)를 따른다. 성능·인증·실네트워크 commit 응답 유실 복구는 검증 범위 밖이다.

2026-10-11 자동 검증: `make check`, `make test-container`(전체 449개), `make compose-check`를 통과했다. 통합·API 테스트는 개발 DB와 분리된 PostgreSQL 테스트 서비스에서 실행했다. `make up`, `make smoke`도 통과했다. Scalar에서 7개 API를 실제 실행해 생성·조회·수정·동일 값 수정·삭제·삭제 후 이력 보존을 확인했다. 자동 코드 중복(409), null 코드(422), 직접 코드 공백 제거, 잘못된 cursor(400), 실제 cursor 다음 페이지를 확인했다. 목록·이력 첫 페이지의 생성 요청 코드와 서버 접근 로그 모두에서 cursor 생략을 확인했다. 테스트용 Brand 두 건은 삭제하고 이력은 보존했다.

## 관련 기능

- [BrandLog](brand-log.md): Brand 변경과 함께 저장하는 이력.
- [Company](company.md): 독립 차원이며 Brand와 직접 참조하지 않는다.
- [Dimension 목차](README.md)

트랜잭션 조립은 [Brand UoW](../../../src/mdm_demo/infrastructure/persistence/units_of_work/brand.py)를 사용한다. 차원과 로그 저장소는 같은 세션을 공유하고, 세션 정리·commit·rollback은 [공통 구현](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py)에서 처리한다.
