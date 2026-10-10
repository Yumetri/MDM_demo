# MDM backend foundation

uv 기반 비동기 FastAPI·SQLAlchemy 백엔드 프로젝트. PostgreSQL·Redis를 Docker Compose로 실행한다.
현재 실행 환경·헬스 체크·Scalar API 문서까지 구현했으며, 업무 기능은 미구현이다.

## 실행

Docker 엔진이 실행 중이고 Docker Compose v2와 `make`가 설치되어 있어야 한다. 로컬 개발용 기본 설정으로 `.env` 없이 실행할 수 있다.

```sh
make up
```

- [Scalar API 문서](http://localhost:8000/docs) — 브라우저에서 CDN 접근 필요.
- [OpenAPI 스키마](http://localhost:8000/openapi.json)
- [헬스 체크](http://localhost:8000/health) — 정상 시 204. 프로세스 생존만 확인하며 DB·캐시 상태를 보장하지 않는다.

주소는 기본 포트 기준이다. 소스 변경 후 `make up`을 다시 실행하면 이미지를 재빌드한다.

## 검증·관리

| 명령 | 용도 |
| --- | --- |
| `make smoke` | 실행 중인 환경의 API·문서·DB·캐시 연결 확인. 브라우저 렌더링은 별도 확인 |
| `make check-container` | 컨테이너에서 Ruff 린트·포맷 및 Pyrefly 타입 검사 |
| `make compose-check` | Compose 설정 검증 |
| `make ps` | 서비스 상태 확인 |
| `make logs` | 로그 보기. Ctrl+C로 로그 보기만 종료 |
| `make down` | 컨테이너 종료·삭제. PostgreSQL 데이터 볼륨 유지 |

## 설정

포트나 DB 설정을 바꾸려면 [.env.example](.env.example)을 `.env`로 복사해 수정한다. 기본 자격증명은 로컬 개발 전용이다.
PostgreSQL은 볼륨에 데이터를 보존하며, 기존 볼륨의 DB 계정·암호는 `.env` 수정만으로 바뀌지 않는다. Redis 캐시는 영속화하지 않는다.

| 파일 | 관리 대상 |
| --- | --- |
| [.python-version](.python-version) | Python 실행 버전 |
| [pyproject.toml](pyproject.toml) | Python 지원 범위·직접 의존성·개발 도구 설정 |
| [uv.lock](uv.lock) | 전체 Python 의존성 잠금 |
| [Dockerfile](Dockerfile) | uv 버전·앱 이미지 구성 |
| [compose.yaml](compose.yaml) | 서비스 설정·PostgreSQL 및 Redis 이미지 버전 |
| [app.py](src/mdm_demo/app.py) | Scalar 번들 버전 |

## 관련 문서

- [서비스 기능맵](docs/features/README.md)
- [기능 문서 템플릿](docs/templates/feature.md)
- [개발·아키텍처·리뷰 규칙](AGENTS.md)
- [API 규약 초안](docs/api-conventions.md)

기능맵에는 구현 전 합의한 업무 규칙도 포함하며, 해당 문서에 구현 전 요구사항임을 표시한다.
