# MDM backend foundation

FastAPI, PostgreSQL, Redis를 Docker Compose로 실행하는 로컬 개발 환경이다.

## 실행

Docker 엔진과 Docker Compose v2가 실행 중이어야 한다.

```sh
make up
make smoke
```

- Scalar API 문서: http://localhost:8000/docs
- OpenAPI 스키마: http://localhost:8000/openapi.json
- 프로세스 상태: http://localhost:8000/health (정상 시 204)
- PostgreSQL과 Redis는 Compose 내부 네트워크에서만 접근한다.
- `make smoke`는 API 컨테이너에서 HTTP 응답, Scalar 문서 HTML·OpenAPI 연결 설정·기존 문서 경로 비활성화, 비동기 PostgreSQL 연결 및 `SELECT 1`, 비동기 Redis `PING`을 확인한다. 브라우저 렌더링 검사는 별도로 수행한다.
- `/health`는 프로세스 생존 검사이며 DB·캐시의 지속적인 정상 동작을 보장하는 readiness 검사가 아니다.

기본값으로 바로 실행할 수 있다. 포트나 로컬 DB 설정을 바꾸려면 `.env.example`을 `.env`로 복사해 수정한다. 기본 자격증명은 로컬 개발 전용이다. 기존 PostgreSQL 볼륨이 있으면 환경변수 변경만으로 DB 계정·암호가 바뀌지 않는다.

```sh
make ps            # 서비스 상태
make logs          # 로그 (Ctrl+C로 로그 보기만 종료)
make down          # 컨테이너 종료·삭제, PostgreSQL 데이터 볼륨 유지
make compose-check # Compose 설정 검증
make check-container # 컨테이너에서 Ruff·Pyrefly 검증
```

정적 검증은 `make check-container`를 기본으로 한다. 호스트에 uv가 있으면 같은 Ruff·Pyrefly 검사를 수행하는 `make check`도 허용한다. 앱 실행은 Compose를 기준으로 한다. 소스 변경 후 `make up`을 다시 실행하면 이미지를 재빌드한다.

API 문서는 [Scalar의 공식 FastAPI 통합](https://scalar.com/products/api-references/integrations/fastapi)을 사용한다. Swagger UI와 ReDoc은 비활성화한다. Scalar JavaScript는 `src/mdm_demo/app.py`에서 고정한 버전을 CDN으로 불러오므로 브라우저에서 CDN 접근이 필요하다. API 테스트 요청은 현재 서버로 직접 보내며 외부 프록시를 사용하지 않는다.

## 환경 관리

- Python 실행 버전: `.python-version`
- Python 지원 범위·직접 의존성·개발 도구 설정: `pyproject.toml`
- 전체 의존성 잠금: `uv.lock`
- uv 버전과 앱 이미지 구성: `Dockerfile`
- PostgreSQL·Redis 이미지 버전: `compose.yaml`

앱 컨테이너 안에서도 uv가 Python을 설치하고 잠금 파일로 환경을 구성한다. 개발 검증을 위해 이미지에 Ruff와 Pyrefly도 포함한다. [uv 공식 Docker 가이드](https://docs.astral.sh/uv/guides/integration/docker/)를 참고한다.

PostgreSQL은 named volume에 데이터를 보존한다. PostgreSQL 18의 볼륨 위치는 [공식 이미지 문서](https://hub.docker.com/_/postgres)에 맞춰 `/var/lib/postgresql`을 사용한다. Redis는 재생성 가능한 캐시로 두며 디스크 영속화를 끄고 128MB 한도와 `allkeys-lru` 정책을 적용한다. 업무별 키·TTL·무효화 정책은 별도로 정한다.

## 구현 범위

현재는 Compose 실행에 필요한 최소 앱과 연결 확인 도구가 있다. 도메인 모델, Data Mapper, UoW, 마이그레이션, 업무 API 및 계약 테스트는 아직 구현하지 않았다. 기준은 [AGENTS.md](AGENTS.md)와 [API 규약 초안](docs/api-conventions.md)을 따른다.

헬스 라우터는 `src/mdm_demo/presentation/routers/health.py`에 있고 `src/mdm_demo/app.py`에서 등록한다. 나머지 계층은 AGENTS.md의 지정 경로에 실제 구현이 필요할 때 추가한다.

미정 사항은 마이그레이션 도구·운영 정책, 업무별 캐시 정책, 테스트 러너·실행 명령·CI 환경이다. API 메시지 언어와 도메인별 오류 코드는 API 규약 초안에서 확정한다.
