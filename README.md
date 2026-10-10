# MDM backend foundation

uv 기반 비동기 FastAPI·SQLAlchemy 백엔드 프로젝트. PostgreSQL·Redis를 Docker Compose로 실행한다.
실행 환경·헬스 체크·Scalar API 문서와 Company CRUD·CompanyLog를 구현했다.
Company와 변경 이력 조회는 PostgreSQL을 사용하며 인증·권한·Company 캐시는 포함하지 않는다.

## 실행

Docker 엔진이 실행 중이고 Docker Compose v2와 `make`가 설치되어 있어야 한다. 로컬 개발용 기본 설정으로 `.env` 없이 실행할 수 있다.

```sh
make up
```

- [Scalar API 문서](http://localhost:8000/docs) — 브라우저에서 CDN 접근 필요.
- [OpenAPI 스키마](http://localhost:8000/openapi.json)
- [헬스 체크](http://localhost:8000/health) — 정상 시 204. 프로세스 생존만 확인하며 DB·캐시 상태를 보장하지 않는다.

Company CRUD는 `/companies`에서 제공하며 구체적인 요청·응답은 [API 규약](docs/api-conventions.md)을 따른다.
회사별 이력은 `/companies/{company_id}/logs`, 로그 단건은 `/company-logs/{log_id}`에서 조회한다. 삭제한 회사도 원래 UUID로 이력을 조회할 수 있다. Scalar에는 성공·실패·경계값 예제와 실행 순서가 있으며, 생성 응답의 UUID와 목록 응답의 cursor를 복사해 테스트한다.
`make up`은 PostgreSQL 준비 → 일회성 `migrate` 서비스의 Alembic 적용 → API 시작 순서로 실행한다. 마이그레이션 실패 시 API 시작을 막는다.

주소는 기본 포트 기준이다. 소스 변경 후 `make up`을 다시 실행하면 이미지를 재빌드한다.

### DataGrip에서 PostgreSQL 연결

`make up` 후 PostgreSQL 데이터 소스를 추가하고 다음 기본값으로 연결한다.

| 항목 | 값 |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `5432` |
| Database | `mdm` |
| User | `mdm` |
| Password | `mdm-local-only` |
| SSL | 비활성화 |

PostgreSQL 포트는 로컬 루프백에만 공개한다. `.env`에서 DB 이름·계정·암호를 변경했다면 실제 설정값을 사용한다. 로컬 5432 포트가 이미 사용 중이면 기존 서비스를 중지하거나 [compose.yaml](compose.yaml)의 호스트 포트를 변경하고 DataGrip에도 같은 포트를 입력한다. 컨테이너 간 연결은 계속 `postgres:5432`를 사용하며 기존 데이터 볼륨은 유지된다.

## 검증·관리

| 명령 | 용도 |
| --- | --- |
| `make smoke` | 실행 중인 환경의 API·문서·DB·캐시 연결 확인. 브라우저 렌더링은 별도 확인 |
| `make test-container` | 별도 PostgreSQL 테스트 서비스에서 마이그레이션·모델 일치 검사와 단위·통합·API 테스트 |
| `make test-unit` | 로컬 uv 환경에서 DB 없는 단위 테스트 |
| `make test-stop` | 테스트 PostgreSQL 종료, 임시 데이터 폐기 |
| `make check-container` | 컨테이너에서 Ruff 린트·포맷 및 Pyrefly 타입 검사. 타입 진단은 경고부터 실패로 처리 |
| `make compose-check` | Compose 설정 검증 |
| `make ps` | 서비스 상태 확인 |
| `make logs` | 로그 보기. Ctrl+C로 로그 보기만 종료 |
| `make down` | 컨테이너 종료·삭제. PostgreSQL 데이터 볼륨 유지 |

테스트는 `test` Compose 프로필의 `postgres-test` 서비스와 `mdm_test` DB를 사용한다. 개발 DB와 볼륨을 공유하지 않으며, 테스트 시작마다 테스트 테이블을 비운다. 테스트 DB 이름이 다르면 실행을 거부한다. tmpfs 데이터는 테스트 DB 종료 시 사라지며 테스트가 끝나도 서비스는 `make test-stop` 전까지 실행된다.

컨테이너 내부 원시 진입점은 `make migrate`, `make migration-check`, `make test`이며 일반 실행은 위 컨테이너 명령을 사용한다. 테스트는 pytest·pytest-asyncio·HTTPX를 사용한다. Alembic은 런타임 마이그레이션 도구이며 패키지 버전은 설정·잠금 파일에서 관리한다.

## 설정

포트나 DB 설정을 바꾸려면 [.env.example](.env.example)을 `.env`로 복사해 수정한다. 기본 자격증명은 로컬 개발 전용이다.
PostgreSQL은 볼륨에 데이터를 보존하며, 기존 볼륨의 DB 계정·암호는 `.env` 수정만으로 바뀌지 않는다. Redis 캐시는 영속화하지 않는다. Company 삭제는 물리 삭제지만 전용 `company_logs`에 원본 UUID를 FK 없이 보존하며 이력은 자동 만료하지 않는다.
`CURSOR_SIGNING_KEY`는 최소 32바이트이며 직접 앱을 실행할 때 반드시 설정한다. Compose에는 로컬 개발용 기본값이 있고 키 교체 시 기존 cursor는 무효화된다.

| 파일 | 관리 대상 |
| --- | --- |
| [.python-version](.python-version) | Python 실행 버전 |
| [pyproject.toml](pyproject.toml) | Python 지원 범위·직접 의존성·개발 도구 설정 |
| [uv.lock](uv.lock) | 전체 Python 의존성 잠금 |
| [Dockerfile](Dockerfile) | uv 버전·앱 이미지 구성 |
| [compose.yaml](compose.yaml) | 서비스 설정·PostgreSQL 및 Redis 이미지 버전 |
| [alembic.ini](alembic.ini), [초기 스키마](migrations/versions/0001_company_dimension.py)·[Company 로그 분리](migrations/versions/0002_split_company_logs.py) | DB 마이그레이션 설정·스키마 이력 |
| [app.py](src/mdm_demo/app.py) | Scalar 번들 버전 |

## 관련 문서

- [서비스 기능맵](docs/features/README.md)
- [기능 문서 템플릿](docs/templates/feature.md)
- [개발·아키텍처·리뷰 규칙](AGENTS.md)
- [API 규약](docs/api-conventions.md)

기능맵에는 구현 전 합의한 업무 규칙도 포함하며, 해당 문서에 구현 전 요구사항임을 표시한다.
