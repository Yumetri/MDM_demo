# 개발 원칙

## 프로젝트 목표

- 이름은 데모지만 테스트와 유지보수를 고려한 백엔드 기본 구조를 만든다.
- Python, FastAPI, SQLAlchemy를 사용하며 I/O는 비동기로 구현한다.
- 클린 아키텍처와 DDD의 전술적 패턴을 적용한다.
- 이 문서는 에이전트의 작업 기준이다. 합의한 규칙이 변경되면 관련 구현과 문서를 함께 갱신한다.

## 환경과 의존성

- Python 설치·버전 선택, 가상환경, 의존성 추가·동기화, Python 명령 실행은 uv로 통일한다.
- Python 실행 버전은 `.python-version`, 지원 범위는 `pyproject.toml`, 해석된 의존성 버전은 `uv.lock`으로 관리한다. 문서에 버전 숫자를 중복 관리하지 않는다.
- 필요한 의존성 추가는 허용한다. 용도를 설명하고 `pyproject.toml`과 `uv.lock`을 함께 갱신한다.
- 기존 의존성의 무관한 일괄 업그레이드는 하지 않는다.
- Ruff와 Pyrefly는 프로젝트의 개발 의존성으로 관리한다. 전역 설치 버전이나 임시 최신 버전에 의존하지 않는다.
- 검증에서는 `uv run --locked`를 사용한다. 잠금 파일 불일치를 자동 갱신으로 숨기지 않는다.
- FastAPI 애플리케이션, PostgreSQL, Redis는 각각 별도 서비스로 Docker Compose에서 실행·관리한다. 애플리케이션의 기본 실행 환경도 Compose로 통일한다.
- 애플리케이션 컨테이너 안에서도 Python 환경과 의존성을 uv로 관리하고 프로젝트의 버전 설정과 `uv.lock`을 따른다.

## 데이터베이스와 캐시

- 데이터베이스는 PostgreSQL, 캐시는 Redis를 사용한다. 두 서비스는 Docker Compose로 실행·관리한다.
- PostgreSQL과 Redis 이미지 버전은 `compose.yaml`에서 명시적으로 고정한다.
- 영속 데이터의 기준은 PostgreSQL이다. Redis는 재생성 가능한 캐시로 사용한다.
- Redis 접근은 애플리케이션의 캐시 포트와 인프라 구현으로 분리한다. 도메인 객체가 Redis 클라이언트에 의존하지 않게 한다.
- 캐시 도입 시 키 규칙, TTL, 무효화 시점, Redis 장애 시 처리 방식을 문서화한다. 구체적인 정책은 유스케이스별로 정한다.
- PostgreSQL 트랜잭션과 Redis 캐시 변경이 하나의 원자적 작업이라고 가정하지 않는다. DB commit 이후 캐시 갱신·무효화 및 실패 처리 전략을 정한다.

## 클린 아키텍처

- 의존성은 바깥에서 안쪽으로 향한다. 도메인은 애플리케이션·인프라·프레젠테이션 계층에 의존하지 않는다.
- `domain`: Entity, Value Object, Aggregate, 도메인 규칙과 도메인 오류를 둔다.
- `application`: 유스케이스를 조율하고 Repository·Unit of Work 등의 포트를 정의한다.
- `infrastructure`: SQLAlchemy 영속성 모델, Data Mapper, Repository 및 Unit of Work 구현을 둔다.
- `presentation`: FastAPI 라우터, 요청·응답 DTO, HTTP 오류 변환을 둔다.
- 구체 구현의 생성과 의존성 연결은 별도의 조립 지점에서 담당한다.
- 도메인 및 애플리케이션 계층에 FastAPI나 SQLAlchemy 의존성을 넣지 않는다. API DTO를 도메인 모델로 사용하지 않는다.

## 풍부한 도메인 모델과 Data Mapper

- Entity는 식별자로 동일성을 판단하고, Value Object는 값으로 동등성을 판단한다. VO는 불변으로 설계한다.
- 의미 있는 도메인 개념은 VO로 표현하고 생성 시 유효성을 보장한다. 의미 없는 원시값 래퍼를 일괄 생성하지 않는다.
- 상태 변경과 불변식 검증은 Entity·VO·Aggregate의 행위로 표현한다. 서비스가 필드를 직접 바꾸는 빈약한 모델을 피한다.
- 여러 객체에 걸친 규칙 중 특정 Entity에 자연스럽게 속하지 않는 규칙은 Domain Service에 둔다.
- Aggregate Root를 통해 내부 상태를 변경하고 Aggregate의 일관성을 보장한다. Aggregate 경계는 업무 규칙을 근거로 정한다.
- 순수한 도메인 계산은 동기로 둔다. DB·네트워크 I/O 경계에 비동기를 적용한다.
- 도메인 객체와 SQLAlchemy 영속성 모델을 분리하고 명시적인 Data Mapper로 상호 변환한다.
- Mapper는 식별자, VO, Aggregate 상태를 손실 없이 복원해야 한다. 도메인 객체에 ORM 세션이나 지연 로딩을 노출하지 않는다.
- 조회 전용 유스케이스는 조회 DTO로 직접 투영할 수 있다. 상태 변경은 도메인 행위를 거친다.

## 비동기 I/O와 Unit of Work

- SQLAlchemy의 비동기 세션과 PostgreSQL용 비동기 드라이버를 사용한다. Redis 접근도 비동기 클라이언트를 사용한다.
- 하나의 작업 단위마다 별도의 세션을 사용한다. 동시에 실행되는 태스크 사이에 세션을 공유하지 않는다.
- 애플리케이션 유스케이스가 작업 경계를 정하고 Unit of Work가 세션 및 트랜잭션 생명주기를 소유한다.
- 저장이 필요한 유스케이스는 UoW의 명시적인 `commit()`을 호출한다. 실제 commit·rollback·세션 정리는 UoW 구현에서만 수행한다.
- 명시적인 commit 없이 종료되거나 예외가 발생하면 rollback하고, 성공·실패 모두 세션을 정리한다. 정상 종료만으로 자동 commit하지 않는다.
- Router·Repository·Mapper는 commit·rollback하지 않는다. Repository의 필요한 flush는 commit과 구분한다.
- 같은 UoW의 Repository들은 같은 세션·트랜잭션을 사용한다. 여러 Repository 변경 중 일부만 저장되는 구조를 만들지 않는다.
- 취소와 commit 실패 시에도 정리가 보장되도록 구현하고 검증한다.
- 외부 API 호출 등 DB 밖의 부작용은 DB rollback으로 취소되지 않는다. 필요할 때 별도의 일관성 전략을 설계한다.

## API 규약과 문서 관리

- API 문서는 `/docs`에서 Scalar로 제공하고 `/openapi.json`을 연결한다. Swagger UI와 ReDoc은 비활성화한다. Scalar Python 패키지와 브라우저 번들 버전을 고정한다.
- 목록 API는 cursor 기반 페이지네이션을 사용한다.
- 응답 구조, 오류 코드, 메시지, HTTP 상태 매핑은 [API 규약](docs/api-conventions.md)을 기준으로 통일한다.
- 공통 응답 DTO, 오류 코드·메시지 카탈로그, 예외 처리기를 재사용한다. 라우터별로 오류 문자열이나 응답 구조를 복제하지 않는다.
- 도메인 오류는 HTTP에 의존하지 않으며 프레젠테이션 계층에서 API 오류로 변환한다.
- API 구현과 함께 OpenAPI 스키마 및 규약 문서를 갱신한다. 새 오류 코드를 추가할 때는 의미·상태·기본 메시지·발생 조건을 기록한다.
- 세부 API 기본안과 아직 미정인 항목은 문서에서 구분한다. 문서에 없는 동작을 합의된 정책처럼 취급하지 않는다.

## 검증과 자동화

- Python 코드·의존성·도구 설정을 변경한 작업은 완료 보고 전에 `make check`를 실행한다.
- `make check`는 아래 검사를 순서대로 실행하며 실패 시 중단한다.
  1. `uv run --locked ruff check .`
  2. `uv run --locked ruff format --check .`
  3. `uv run --locked pyrefly check`
- 포맷 수정 명령은 `make format`이다. 요청과 무관한 기존 파일을 일괄 수정하지 않는다.
- Ruff와 Pyrefly는 정적 검증이다. 기능 테스트를 대체하지 않는다.
- 도메인 불변식, Mapper 왕복 변환, UoW commit·rollback, API 오류 계약, cursor 경계는 관련 구현 시 동작 테스트로 검증한다.
- 도메인 테스트는 DB 없이 실행하고, 영속성·트랜잭션 테스트는 실제 PostgreSQL의 동작을 검증한다. 캐시 통합 테스트는 실제 Redis에서 만료·무효화 등 관련 동작을 검증한다.
- 테스트 러너와 테스트 명령은 초기 구현 시 확정하고 이 문서와 Makefile에 함께 반영한다.
- CI를 추가할 때도 같은 `make check`를 호출한다. 로컬과 CI의 검증 규칙을 별도로 복제하지 않는다.
- Compose 구성 변경 시 `make compose-check`로 설정을 검증하고, 가능하면 `make up`과 `make smoke`로 실제 기동·연결을 확인한다. 컨테이너 정적 검증은 `make check-container`로 실행한다.
- 검사 실패를 무시하거나 규칙을 완화해 통과시키지 않는다. 실행하지 못한 검사는 이유와 함께 보고한다.

## 사용자 허가가 필요한 작업

- **리팩터링은 시작 전에 반드시 사용자 허가를 받는다.** 대상, 이유, 변경 범위를 먼저 설명한다.
- 기능 구현 허가를 관련 코드의 구조 재편·이름 변경·공통화 허가로 확대 해석하지 않는다.
- **커밋 전에 반드시 사용자 허가를 받는다.** 검토 가능한 변경 내용과 검증 결과를 먼저 제시한다.
- **푸시 전에 반드시 사용자 허가를 받는다.** 커밋 허가를 푸시 허가로 간주하지 않는다.
- 허가는 사용자가 승인한 작업 범위에만 적용한다. 후속 작업의 포괄적 허가로 간주하지 않는다.
- 의존성 추가 자체에는 별도 허가가 필요하지 않지만, 추가 과정에 리팩터링이 필요하면 먼저 허가를 받는다.

## 초기 구축 시 미정 사항

- 마이그레이션 도구 및 운영 정책.
- 구체적인 캐시 정책.
- 테스트 러너와 실행 명령, CI 실행 환경.
- API 규약 초안의 메시지 언어 및 도메인별 오류 코드.

Compose 실행용 최소 FastAPI 앱과 `pyproject.toml`, `uv.lock`이 있다. Python 버전은 `.python-version`, uv 버전은 `Dockerfile`, DB·캐시 이미지 버전은 `compose.yaml`에서 관리한다. 실행·검증 방법은 `README.md`를 따른다. 도메인·UoW·업무 API는 아직 구현하지 않았다.
