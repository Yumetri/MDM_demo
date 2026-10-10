# Company

Company CRUD와 변경 이력을 구현했다. 작업은 [이슈 #2](https://github.com/Yumetri/MDM_demo/issues/2), 공통 원칙은 [이슈 #1](https://github.com/Yumetri/MDM_demo/issues/1)에서 추적한다.

## 제공 기능

- 제품을 출시하는 업체의 회사명과 고유코드를 등록·조회·수정·삭제한다.
- 진입점은 `/companies` 및 `/companies/{company_id}`이며 [API 규약](../../api-conventions.md)에서 메서드·요청·응답·오류 계약을 관리한다.
- 로컬 개발용 기능이다. 인증·권한, 검색·선택 정렬, Company 캐시는 구현 범위 밖이다. 이력 조회는 [CompanyLog](company-log.md)에서 제공한다.

## 업무 규칙과 제약

| 조건 | 규칙·결과 | 구현 근거 |
| --- | --- | --- |
| 회사명 | 양끝 공백 제거 후 1~200자, 내부 공백 보존, 중복 허용 | `CompanyName` |
| 직접 입력 코드 | ASCII 영문 3자, 공백 불허, 대문자 정규화 | `CompanyCode` |
| 코드 생략 | 회사명의 ASCII 영문만 추출해 앞 3자를 대문자로 생성 | `CompanyCode.from_name` |
| 자동 생성 실패 | 영문이 3자 미만이거나 생성 코드가 중복이면 실패, 임의 재생성 없음 | 도메인·Company 유스케이스 |
| 코드 유일성 | Company 테이블 안에서 유일함. `abc`와 `ABC`는 같은 코드 | `uq_companies_code` |
| 등록 후 코드 변경 | 금지 | 불변 코드·수정 요청 스키마 |
| 회사명 수정 | 현재 이름을 변경하고 조회에 반영 | `Company.rename` |
| 같은 이름으로 수정 | 성공 응답, 데이터·수정 시각·이력 변경 없음 | `Company.rename`, 유스케이스 |
| 삭제 | 물리 삭제, 이력 보존, 삭제 코드 재사용 시 새 식별자 부여 | 삭제·등록 유스케이스 |
| 생성·수정·삭제 | Company와 이전·이후 값의 로그를 함께 저장 | 동일 UoW |

자동 생성 예: `Samsung` → `SAM`, `LG Electronics` → `LGE`, `3M Korea` → `MKO`. `삼성전자`·`LG`는 실패한다. 이 규칙을 다른 차원에 자동 적용하지 않는다.

입력 문자열 중 PostgreSQL text에 저장할 수 없는 NUL과 UTF-8로 표현할 수 없는 단독 surrogate는 도메인에서 거부한다. 정상 한글·이모지는 보존한다. 코드 null·빈 값 처리 등 HTTP 입력 계약은 API 규약을 따른다.

## 처리 흐름

1. 도메인이 이름·직접 코드를 검증·정규화하거나 자동 코드를 생성한다.
2. 요청마다 새 UoW와 세션을 사용한다. 등록 시 Company 저장·flush로 코드 유일성을 검사한다.
3. 수정·삭제는 행 잠금을 획득한 현재 값을 읽고 이전 스냅샷을 만든다.
4. 도메인 메서드로 변경한 뒤 Company와 CompanyLog를 같은 세션으로 저장한다.
5. 유스케이스가 명시적으로 commit한다. 조회와 변경 없는 수정은 commit하지 않고 정리한다.

## 데이터와 트랜잭션

- `companies`: UUID v4 PK, 회사명, 코드, UTC 생성·수정 시각. 도메인 객체와 ORM 모델은 Mapper로 변환한다.
- `company_logs`: [CompanyLog](company-log.md) 참조. `company_id`는 NOT NULL UUID이며 FK 없이 삭제 후에도 보존한다.
- 코드 UNIQUE·코드 형식·이름 길이 제약은 DB에도 둔다. 이름 양끝의 유니코드 공백 정리는 도메인에서 수행하며 DB의 `btrim` 제약은 일반 공백을 검사한다.
- 동시 수정·삭제는 `SELECT … FOR UPDATE`로 직렬 처리한다. 나중에 처리된 수정이 최종 이름이 되며 오래된 클라이언트 값을 별도로 거부하지 않는다.
- 알려진 코드 UNIQUE 위반만 중복으로 변환한다. 다른 DB 오류는 중복으로 오인하지 않는다.
- 미커밋 종료·예외에는 rollback한다. 취소 중에도 정리 작업이 끝날 때까지 기다려 세션을 닫는다. commit 응답이 네트워크에서 유실된 경우 결과 확정·자동 재시도를 제공하지 않는다.

## 조회와 인덱스

| 조회 | 인덱스 | 역할 |
| --- | --- | --- |
| 단건·수정·삭제 대상 | PK(id) | 식별자 검색과 대상 행 잠금 |
| 코드 유일성 | UNIQUE(code) | 동시 등록에서도 중복 방지 |
| 목록 | (created_at, id) | 고정 정렬 및 keyset 경계 조회 지원 |

cursor 구현·경계와 목록의 변경 중 일관성 범위는 API 규약을 따른다. 실제 쿼리 실행은 통합 테스트로 확인했다. 대표 규모 데이터에서의 EXPLAIN·성능 측정은 미확인이며 인덱스 사용을 단정하지 않는다.

## 캐시

Company 조회에는 캐시를 적용하지 않는다. 모두 PostgreSQL에서 읽으며 키·TTL·무효화·Redis 장애 fallback은 해당하지 않는다. 기존 Redis 서비스는 유지한다.

## 구현과 검증

| 구분 | 근거 |
| --- | --- |
| 도메인 | [Company](../../../src/mdm_demo/domain/entities/company.py), [이름](../../../src/mdm_demo/domain/value_objects/company_name.py), [코드](../../../src/mdm_demo/domain/value_objects/company_code.py) |
| 유스케이스 | [CompanyUseCases](../../../src/mdm_demo/application/use_cases/company.py) |
| DB·Mapper | [모델](../../../src/mdm_demo/infrastructure/persistence/models/company.py), [Repository](../../../src/mdm_demo/infrastructure/persistence/repositories/company_repository.py), [Mapper](../../../src/mdm_demo/infrastructure/persistence/mappers/company_mapper.py) |
| 트랜잭션·스키마 | [UoW](../../../src/mdm_demo/infrastructure/persistence/unit_of_work.py), [초기 마이그레이션](../../../migrations/versions/0001_company_dimension.py), [로그 분리](../../../migrations/versions/0002_split_company_logs.py) |
| HTTP | [라우터](../../../src/mdm_demo/presentation/routers/company.py), [스키마](../../../src/mdm_demo/presentation/schemas/company.py) |
| 단위 테스트 | [도메인](../../../tests/unit/domain/test_company.py), [유스케이스](../../../tests/unit/application/test_company.py), [cursor](../../../tests/unit/application/test_cursor.py) |
| 실제 PostgreSQL 검증 | [영속성·원자성·동시성](../../../tests/integration/persistence/test_company.py), [API 계약](../../../tests/api/test_company.py) |

실행 진입점과 테스트 DB 격리는 [README](../../../README.md)의 검증 안내를 따른다. 캐시·인증과 실네트워크 commit 응답 유실 복구는 검증 대상이 아니다.

## 관련 기능

- [CompanyLog](company-log.md): 변경과 함께 커밋하는 이력.
- 다른 차원과의 구체적인 참조 관계는 미정이다. 향후 참조가 추가되면 참조 중 삭제 제한을 해당 기능과 함께 설계한다.
- [Dimension 목차](README.md)
