# 작업 기준

## 환경

- 테스트와 유지보수를 고려한 Python·FastAPI·SQLAlchemy 백엔드를 만든다. Python 설치·가상환경·의존성·명령 실행은 컨테이너 안에서도 uv로 통일한다.
- FastAPI·PostgreSQL·Redis는 별도 Docker Compose 서비스로 실행한다. PostgreSQL은 영속 데이터 기준, Redis는 재생성 가능한 캐시다.
- Python·패키지·이미지·Scalar 번들 버전은 설정·잠금 파일에서 고정한다. 파일별 위치와 실행법은 [README](README.md)를 따른다. 문서에 버전 숫자를 중복하지 않는다.
- 필요한 의존성 추가는 허용한다. 용도를 설명하고 `pyproject.toml`·`uv.lock`을 함께 갱신하며 무관한 업그레이드는 하지 않는다.
- 작업 완료 전에 변경 사항을 README와 비교한다. 실행 전제·명령, 접속 주소, 설정·버전 관리 파일 위치, 데이터 보존 방식, 구현 범위가 달라지면 같은 작업에서 README를 갱신한다. 해당 안내에 영향이 없는 내부 구현 변경은 기록하지 않고, 세부 규칙·API 계약은 기존 문서 링크로 안내한다.

## 폴더와 의존성

아래 경로는 `src/mdm_demo/` 기준이다. 구현이 생길 때 해당 경로에 배치한다. 빈 폴더·클래스를 미리 만들지 않는다.

| 경로 | 책임 |
| --- | --- |
| `app.py` | FastAPI 생성, 공통 미들웨어·예외 처리·문서 설정, 선택한 기능 등록 |
| `composition/` | 실행 자원 수명 관리, 차원별 구체 구현체 조립, 명시적 기능 목록 |
| `domain/entities/` | Entity와 Aggregate Root |
| `domain/value_objects/` | 불변 Value Object |
| `domain/services/`, `domain/errors/` | 여러 도메인 객체의 업무 규칙, HTTP와 무관한 오류 |
| `application/use_cases/`, `application/dto/` | 유스케이스 실행·UoW 경계, 입력·출력 DTO |
| `application/errors/`, `application/ports/cursors/` | 공통 오류와 차원별 오류, 차원별 cursor 타입·인터페이스 |
| `application/ports/repositories/` | Aggregate별 Repository 인터페이스 |
| `application/ports/unit_of_work.py`, `application/ports/units_of_work/`, `application/ports/cache.py` | 공통 트랜잭션·차원별 UoW·캐시 인터페이스 |
| `infrastructure/persistence/models/` | SQLAlchemy 영속성 모델 |
| `infrastructure/persistence/mappers/` | 도메인 ↔ ORM 변환 |
| `infrastructure/persistence/repositories/` | Repository 구현 |
| `infrastructure/persistence/session.py`, `infrastructure/persistence/unit_of_work.py`, `infrastructure/persistence/units_of_work/` | 엔진·세션 팩토리, 공통 트랜잭션 처리·차원별 SQLAlchemy UoW |
| `infrastructure/cache/redis_cache.py` | Redis 캐시 구현 |
| `presentation/routers/`, `presentation/schemas/` | FastAPI 엔드포인트, HTTP 요청·응답 모델 |
| `presentation/dependencies/` | 조립된 의존성을 전달하는 FastAPI 어댑터 |
| `presentation/error_catalog.py`, `presentation/exception_handlers.py` | API 오류 코드·메시지·상태 매핑, 공통 예외 응답 변환 |

- 오류·cursor·의존성 제공자는 차원별 모듈에 둔다. 패키지 `__init__.py`에는 공통 정의만 두며 차원별 정의를 일괄 재노출하지 않는다.
- Repository·Mapper 파일명은 `<aggregate>_repository.py`, `<aggregate>_mapper.py`를 사용한다. 업무 로직을 담는 최상위 `utils/`, `common/`, `helpers.py`는 만들지 않는다.
- 클린 아키텍처의 프로젝트 내부 의존성은 `domain → domain`, `application → domain/application`, `infrastructure → domain/application/infrastructure`, `presentation → application/presentation`만 허용한다. `app.py`와 `composition/`만 전체 계층을 조립하며 업무 규칙을 구현하지 않는다. 나머지 계층은 `composition/`을 import하지 않는다.
- `domain`·`application`에서 FastAPI·SQLAlchemy·Redis 클라이언트를 import하지 않는다. `presentation`에서 SQL·Redis를 직접 호출하거나 인프라 구현체를 생성하지 않는다.

## 도메인·트랜잭션·캐시

- DDD 전술 패턴을 적용한다. Entity는 식별자, VO는 값으로 동등성을 판단한다. VO는 불변이며 생성 시 유효성을 검증한다.
- 상태 변경·불변식은 도메인 메서드에 둔다. 유스케이스·라우터는 Entity 필드를 직접 대입하지 않는다. Aggregate 내부 변경은 Root를 거치고 경계는 업무 규칙으로 정한다.
- 도메인 객체·ORM 모델·API DTO를 별도 클래스로 분리한다. 도메인 ↔ ORM 변환은 `infrastructure/persistence/mappers/`에서 손실 없이 수행하며 도메인에 세션·지연 로딩을 노출하지 않는다.
- 조회 전용 DTO 투영은 허용한다. 순수 도메인 계산은 동기, DB·네트워크 I/O는 비동기로 구현한다.
- 유스케이스가 `async with uow`로 작업을 시작하고 저장 성공 시 `await uow.commit()`을 호출한다. 실제 commit·rollback·세션 종료는 UoW 구현만 수행한다. Repository의 flush는 허용한다.
- 유스케이스는 필요한 저장소만 선언한 차원별 UoW Protocol에 의존한다. 차원 데이터와 로그 저장소는 같은 세션을 사용하며 commit·rollback·취소·종료 구현은 공통 UoW에서 재사용한다. 여러 차원의 원자적 변경이 필요한 경우 해당 작업의 저장소를 한 세션에 묶는 UoW를 정의한다.
- 미커밋 종료·예외에는 rollback한다. 취소·commit 실패에도 세션을 정리하고 정상 종료만으로 자동 commit하지 않는다. 같은 UoW의 Repository는 세션을 공유하되 동시 태스크 간에는 공유하지 않는다.
- 캐시 키·TTL·무효화·장애 대응을 유스케이스별로 문서화한다. DB 변경에 따른 캐시 갱신·무효화는 commit 이후 수행하고 실패 처리 전략을 정의한다. DB와 Redis의 원자성을 가정하지 않는다.

## API

- Scalar는 `/docs`, OpenAPI는 `/openapi.json`에서 제공한다. Swagger UI·ReDoc은 비활성화한다. 목록 조회는 cursor 방식으로 구현한다.
- 공통 응답 모델·오류 카탈로그·예외 처리기는 위 지정 경로에 두고 재사용한다. 라우터에서 공통 응답 구조·오류 메시지를 개별 작성하지 않는다. 도메인 오류는 application 경계에서 전달할 오류로 변환하고 presentation에서 HTTP 응답으로 매핑한다.
- 필드·오류 코드·메시지·HTTP 상태·페이지네이션 계약은 [API 규약](docs/api-conventions.md)에서만 관리한다. 계약 변경 시 구현·OpenAPI·규약·관련 테스트를 함께 수정하며 초안을 임의로 확정하지 않는다.
- OpenAPI에는 각 API의 정상 요청·응답, 대표 실패, 경계값과 실수하기 쉬운 입력을 이름 있는 `examples`로 충분히 제공한다. Scalar·Swagger 같은 OpenAPI UI에서 예제를 선택해 HTTP 요청을 실행할 수 있도록 본문·경로·쿼리 예제를 해당 위치에 선언하며, 스키마 설명만으로 대신하지 않는다. 현재 문서 UI는 Scalar를 유지한다.
- 예제마다 예상 HTTP 상태·오류 코드와 필요한 사전 조건을 적는다. 생략과 null, 빈 값·공백, 형식·길이·범위 위반, 중복, 없는 대상, 변경 없는 수정, 삭제 후 조회, cursor 오류 등 해당 API의 주요 분기를 포함한다. 204는 본문 예제를 만들지 않는다.
- 동적인 UUID·서명 cursor는 실제 응답에서 복사할 위치와 요청 순서를 안내한다. 고정 예제 UUID의 존재를 가정하거나 가짜 cursor를 정상 예제로 제시하지 않는다. 중복·삭제처럼 상태에 의존하는 예제는 생성·정리 절차를 제공하고 비밀정보·개인정보는 사용하지 않는다.
- API 변경 시 예제와 응답 모델·오류 카탈로그를 함께 갱신한다. 예제가 OpenAPI에 노출되는지와 대표 예제의 실제 응답을 테스트하고, 문서 UI 변경은 실제 브라우저에서 예제 선택·요청 실행까지 검증한다.
- 여러 API에 걸친 공통 테스트 순서는 문서 상단에 한 번만 안내한다. 개별 API 설명에는 해당 요청의 동작·주의점만 두고 공통 안내 전체를 반복하지 않는다.
- 문서 UI를 새로 열었을 때 기본 요청은 정상 경로로 실행할 수 있어야 한다. 생략해야 정상인 선택 파라미터(첫 페이지 cursor 등)에 실패 예제를 기본값처럼 자동 입력하지 않는다. 이런 경우 실패 입력은 파라미터 설명에 수동 실행 방법으로 안내하고, 생성된 요청 코드와 실제 전송 요청 모두에서 생략되는지 확인한다.

## 기능 문서

- [서비스 기능맵](docs/features/README.md)은 전체 목차 → 영역별 목차 → 기능별 문서로 연결한다. 목차에는 기능 목록과 링크를 두고, 기능 설명은 개별 문서에서 관리한다.
- 새 기능 문서는 [공통 템플릿](docs/templates/feature.md)을 복사해 `docs/features/<영역>/<기능>.md`에 작성하고 영역 목차에 연결한다. 사용자와 합의한 구체적인 업무 규칙은 구현 전에도 기록하되, 실제 구현과 구분하고 미정 항목을 단정하지 않는다. 영역 소개에 개별 기능의 목적을 일반화하거나 상태표를 넣지 않는다.
- 구현 티켓에는 차원별 상세 명세를 복제하지 않고 공통 원칙과 기능 문서의 위치를 기록한다. 개별 차원의 필드·코드 생성 규칙 등은 기능 문서에서 관리하고, API 계약은 기존 API 규약을 참조한다.
- 기능 변경 시 업무 규칙·데이터·인덱스·캐시·검증 등 관련 절과 코드 링크를 같은 작업에서 갱신한다. 기능 삭제 시 문서와 참조를 정리하고, 영역 추가·삭제 시 전체 목차도 갱신한다. 해당 없는 항목은 이유와 함께 간단히 표시하고, 사용하지만 확인하지 못한 동작은 미확인으로 구분한다.

## 병렬 개발·통합

- 착수 시 기준 브랜치·커밋, 담당 기능, 수정 예정 공통 파일, 선행 PR과 통합 순서를 작업 계획에 명시한다. 접근 가능한 진행 중 작업과 변경 경로를 비교하고 공통 계약이 겹치면 담당 범위·선행 변경을 먼저 정한다. 다른 작업의 상태를 확인하지 못한 경우 독립적이라고 단정하지 않는다. 작업별 진행 정보는 작업 계획·티켓·PR에서 관리하며 이 문서에 누적하지 않는다.
- 독립 기능은 별도 브랜치·worktree에서 개발한다. 병렬 실행 시 Compose 프로젝트명·이미지 태그·호스트 포트·DB·볼륨을 작업별로 격리하고 다른 작업의 자원을 초기화하거나 종료하지 않는다. worktree만으로 실행 자원이나 병합 충돌이 격리된다고 가정하지 않는다.
- 여러 기능이 의존하는 공통 타입·인터페이스·API 계약 변경은 기능 구현과 분리한 선행 PR로 관리한다. 종속 작업은 그 기준과 선행 PR을 명시하고 같은 공통 변경을 각자 구현하지 않는다. 독립 기능 PR 사이에 불필요한 의존성을 만들지 않는다.
- 신규 기능의 업무 규칙·오류·cursor·UoW·조립·fixture는 기존 계층 규칙에 따라 기능별 파일에 둔다. 기존 기능 파일도 수정해야 한다면 필요한 동작과 영향 범위를 설명한다. 여러 기능에 실제로 필요한 공통 동작은 재사용하되 기능 추가만으로 공통 인터페이스에 모든 기능의 의존성을 늘리지 않는다.
- `composition/registry.py`, fixture 등록 목록, 기능 목차 등 공통 등록 지점에서는 해당 기능의 등록만 최소 범위로 변경한다. 무관한 재정렬·포맷·이동·이름 변경을 섞지 않는다. 필요한 구조 변경은 별도 리팩터링 범위로 설명하고 기존 허가 절차를 따른다. 공통 파일 변경이나 변경 파일 수만으로 PR을 금지하지 않는다.
- 최종 리뷰 전에 원격 기준 브랜치의 최신 상태를 확인·반영한다. 기본 기준은 `main`이며 선행 PR에 종속된 작업은 해당 기준 브랜치를 사용한다. 충돌은 양쪽 기능의 의도를 확인해 해결하고 한쪽 내용을 일괄 선택하지 않는다. 반영 후 변경 종류에 맞는 검사를 수행하고 최종 패치를 고정한다. 실행 코드·의존성·조립에 영향이 있으면 전체 앱 조립·API 검증도 수행한다. 리뷰 후 기준 반영이나 추가 수정으로 패치가 바뀌면 관련 검사와 두 필수 리뷰를 다시 수행한다.
- 병렬 마이그레이션은 고유한 revision ID와 파일명을 사용한다. 통합 시 이 프로젝트의 단일 head를 확인하고, 여러 head가 생기면 스키마 변경의 호환성을 검토한 뒤 필요한 merge revision을 추가한다. 이미 공유·적용한 마이그레이션의 ID·부모·내용을 충돌 회피 목적으로 바꾸지 않는다. 빈 DB와 각 선행 head에서 최신 head로의 업그레이드를 검증하며, merge revision만으로 의미상 충돌까지 해결됐다고 간주하지 않는다.
- 경로 등록 검사는 접두사를 반영한 전체 HTTP 라우트에서 수행한다. 같은 HTTP 메서드에서 파라미터 이름만 다른 동일 매처는 중복으로 처리하고 converter의 매칭 조건은 보존한다. `/docs`·`/openapi.json`·`/health`와 같은 메서드로 겹치는 동적 경로도 거부한다. 예약 경로·메서드는 실제 앱 소유 라우트에서만 수집하며, 같은 URL의 기능 라우트가 예약 메서드를 늘리지 않도록 한다. 일반 경로 사이의 부분 겹침을 모두 판정하는 검사는 아니므로 넓은 동적 경로는 라우팅 순서·OpenAPI 표현을 별도로 검토한다.
- 기능별 격리 테스트와 전체 앱 통합 테스트를 함께 유지한다. 계층 의존성·중복 등록·마이그레이션 head처럼 자동 판정 가능한 통합 조건은 테스트·CI로 검증하고 검사 진입점은 `Makefile`에서 관리한다. 아직 자동화하지 않은 조건은 수동 확인 여부를 보고하며 검사 완료로 단정하지 않는다.

## 검증

완료 보고 전에 변경 종류에 해당하는 검사를 모두 실행한다. 원시 검사 명령은 `Makefile`에서만 관리하며 CI도 같은 진입점을 사용한다.

| 변경 | 필수 검증 |
| --- | --- |
| Python·의존성·검사 설정 | `make check-container` 또는 동일한 Ruff·Pyrefly 검사를 수행하는 `make check` |
| Compose·Dockerfile·앱 시작 설정 | `make compose-check`, `make up`, `make smoke` |
| API 문서 UI | HTTP 검사와 실제 브라우저 렌더링·요청 실행 |
| 업무 동작 | 관련 단위·통합·API 테스트 |
| Markdown만 변경 | `git diff --check`, 링크 대상·규칙 간 모순 확인 |

- 검증은 `uv run --locked`를 사용한다. 실패를 숨기거나 기준을 완화하지 않으며 실행하지 못한 검사와 이유를 보고한다. 포맷 수정은 `make format`을 사용하되 무관한 파일을 수정하지 않는다.
- 기능 조립은 `composition/registry.py`의 명시적인 목록을 사용한다. 차원별 조립은 해당 모듈에서 수행하고 파일 탐색·import 부작용으로 기능을 자동 등록하지 않는다. 실제 앱이 생성한 실행 자원은 lifespan에서 종료하며 테스트 fixture가 제공한 자원은 해당 fixture만 종료한다.
- 차원별 테스트 fixture는 `tests/fixtures/`에 두고 공통 앱 팩토리를 사용한다. 기존 API 테스트에 다른 차원의 서비스 인자를 추가하지 않는다. 격리 API 검사와 전체 앱 통합 검사를 함께 유지한다.
- 테스트는 `tests/unit/domain/`, `tests/unit/application/`, `tests/integration/persistence/`, `tests/integration/cache/`, `tests/api/`에 배치한다. 도메인 테스트는 DB 없이, 영속성·캐시 통합 테스트는 실제 PostgreSQL·Redis에서 실행한다.
- 관련 불변식·Mapper 왕복·UoW 성공/실패·API 오류·cursor 경계를 동작 테스트로 검증한다. 정적 검사는 이를 대체하지 않는다. 테스트 환경 구축 시 실행 명령을 Makefile에 추가한다.

## 리뷰와 허가

- 리팩터링·커밋·푸시는 각각 대상·범위를 설명하고 사전 허가를 받는다. 기존 승인은 해당 범위에만 적용하며 같은 범위의 허가를 반복 요청하지 않는다. 의존성 추가 허가가 리팩터링 허가를 포함하지는 않는다.
- 문서·설정을 포함한 모든 커밋 전에 `codex-security:security-diff-scan`과 `review-agent`를 수행한다. 설치된 `SKILL.md` 전체 절차를 따르고 스킬 누락·실행 실패·검토 누락을 보고하며 완료 전 커밋하지 않는다.
- 전체 커밋 대상의 기준 커밋·패치 식별자를 기록하고 리뷰 중 수정하지 않는다. 문제·결함 후보가 나오면 주 에이전트가 **별도 서브에이전트 2개**에 같은 패치·증거·요구사항을 주고 독립적으로 병렬 재검토시킨다.
- 재검토자는 읽기 전용으로 실재성·발생 조건·영향·반례·수정 대안을 확인한다. 파일 수정·커밋·푸시·외부 게시·추가 위임을 하지 않는다.
- 주 에이전트는 우선순위·파일/줄·증거·두 의견의 일치/불일치·수정안·검증 계획을 보고한다. **사용자와 수정 여부·방향·범위를 합의한 뒤에만 수정**한다. 최초 구현·커밋 요청을 발견 사항의 자동 수정 허가로 해석하지 않는다.
- 합의한 수정 후 관련 검사와 두 필수 리뷰를 최종 패치에 다시 수행한다. 새 문제·미해결 문제도 같은 절차를 따른다. 미수정 문제를 수용하면 결정·잔여 위험을 기록하고 해당 상태의 커밋 승인을 받는다.
- 문제가 없으면 리뷰 결과·검증 범위를 보고하고 커밋 대상과 검토한 패치의 일치를 확인한다. 추가 변경은 다시 검토한다. 리뷰 완료가 커밋·푸시 허가를 대신하지 않는다.

스킬 위치: [security-diff-scan](/Users/tagit/.codex/plugins/cache/openai-curated-remote/codex-security/0.1.32/skills/security-diff-scan/SKILL.md), [review-agent](/Users/tagit/.codex/skills/.system/review-agent/SKILL.md). 경로가 바뀌면 같은 이름의 스킬을 찾아 사용한다.
