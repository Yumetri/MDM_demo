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
| `app.py` | FastAPI 생성, 구체 구현체 조립, 라우터 등록 |
| `domain/entities/` | Entity와 Aggregate Root |
| `domain/value_objects/` | 불변 Value Object |
| `domain/services/`, `domain/errors.py` | 여러 도메인 객체의 업무 규칙, HTTP와 무관한 오류 |
| `application/use_cases/`, `application/dto/` | 유스케이스 실행·UoW 경계, 입력·출력 DTO |
| `application/ports/repositories/` | Aggregate별 Repository 인터페이스 |
| `application/ports/unit_of_work.py`, `application/ports/cache.py` | 비동기 UoW·캐시 인터페이스 |
| `infrastructure/persistence/models/` | SQLAlchemy 영속성 모델 |
| `infrastructure/persistence/mappers/` | 도메인 ↔ ORM 변환 |
| `infrastructure/persistence/repositories/` | Repository 구현 |
| `infrastructure/persistence/session.py`, `infrastructure/persistence/unit_of_work.py` | 엔진·세션 팩토리, SQLAlchemy UoW 구현 |
| `infrastructure/cache/redis_cache.py` | Redis 캐시 구현 |
| `presentation/routers/`, `presentation/schemas/` | FastAPI 엔드포인트, HTTP 요청·응답 모델 |
| `presentation/dependencies.py` | 조립된 의존성을 전달하는 FastAPI 어댑터 |
| `presentation/error_catalog.py`, `presentation/exception_handlers.py` | API 오류 코드·메시지·상태 매핑, 공통 예외 응답 변환 |

- Repository·Mapper 파일명은 `<aggregate>_repository.py`, `<aggregate>_mapper.py`를 사용한다. 업무 로직을 담는 최상위 `utils/`, `common/`, `helpers.py`는 만들지 않는다.
- 클린 아키텍처의 프로젝트 내부 의존성은 `domain → domain`, `application → domain/application`, `infrastructure → domain/application/infrastructure`, `presentation → application/presentation`만 허용한다. `app.py`는 전체 계층을 조립하되 업무 규칙을 구현하지 않는다.
- `domain`·`application`에서 FastAPI·SQLAlchemy·Redis 클라이언트를 import하지 않는다. `presentation`에서 SQL·Redis를 직접 호출하거나 인프라 구현체를 생성하지 않는다.

## 도메인·트랜잭션·캐시

- DDD 전술 패턴을 적용한다. Entity는 식별자, VO는 값으로 동등성을 판단한다. VO는 불변이며 생성 시 유효성을 검증한다.
- 상태 변경·불변식은 도메인 메서드에 둔다. 유스케이스·라우터는 Entity 필드를 직접 대입하지 않는다. Aggregate 내부 변경은 Root를 거치고 경계는 업무 규칙으로 정한다.
- 도메인 객체·ORM 모델·API DTO를 별도 클래스로 분리한다. 도메인 ↔ ORM 변환은 `infrastructure/persistence/mappers/`에서 손실 없이 수행하며 도메인에 세션·지연 로딩을 노출하지 않는다.
- 조회 전용 DTO 투영은 허용한다. 순수 도메인 계산은 동기, DB·네트워크 I/O는 비동기로 구현한다.
- 유스케이스가 `async with uow`로 작업을 시작하고 저장 성공 시 `await uow.commit()`을 호출한다. 실제 commit·rollback·세션 종료는 UoW 구현만 수행한다. Repository의 flush는 허용한다.
- 미커밋 종료·예외에는 rollback한다. 취소·commit 실패에도 세션을 정리하고 정상 종료만으로 자동 commit하지 않는다. 같은 UoW의 Repository는 세션을 공유하되 동시 태스크 간에는 공유하지 않는다.
- 캐시 키·TTL·무효화·장애 대응을 유스케이스별로 문서화한다. DB 변경에 따른 캐시 갱신·무효화는 commit 이후 수행하고 실패 처리 전략을 정의한다. DB와 Redis의 원자성을 가정하지 않는다.

## API

- Scalar는 `/docs`, OpenAPI는 `/openapi.json`에서 제공한다. Swagger UI·ReDoc은 비활성화한다. 목록 조회는 cursor 방식으로 구현한다.
- 공통 응답 모델·오류 카탈로그·예외 처리기는 위 지정 경로에 두고 재사용한다. 라우터에서 공통 응답 구조·오류 메시지를 개별 작성하지 않는다. 도메인 오류는 application 경계에서 전달할 오류로 변환하고 presentation에서 HTTP 응답으로 매핑한다.
- 필드·오류 코드·메시지·HTTP 상태·페이지네이션 계약은 [API 규약](docs/api-conventions.md)에서만 관리한다. 계약 변경 시 구현·OpenAPI·규약·관련 테스트를 함께 수정하며 초안을 임의로 확정하지 않는다.

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
