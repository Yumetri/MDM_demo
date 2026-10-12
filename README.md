# MDM backend foundation

uv 기반 비동기 FastAPI·SQLAlchemy 백엔드 프로젝트. PostgreSQL·Redis를 Docker Compose로 실행한다.
실행 환경·헬스 체크·Scalar API 문서와 Company·Model·Brand·Country·Category·Year CRUD·CompanyLog·ModelLog·BrandLog·CountryLog·CategoryLog·YearLog를 구현했다.
Company·Model·Brand·Country·Category·Year와 변경 이력 조회는 PostgreSQL을 사용하며 인증·권한·차원 캐시는 포함하지 않는다.

## 실행

Docker 엔진이 실행 중이고 Docker Compose v2와 `make`가 설치되어 있어야 한다. 로컬 개발용 기본 설정으로 `.env` 없이 실행할 수 있다.

```sh
make up
```

- [Scalar API 문서](http://localhost:8000/docs) — 브라우저에서 CDN 접근 필요.
- [OpenAPI 스키마](http://localhost:8000/openapi.json)
- [헬스 체크](http://localhost:8000/health) — 정상 시 204. 프로세스 생존만 확인하며 DB·캐시 상태를 보장하지 않는다.

Company CRUD는 `/companies`, Model CRUD는 `/models`에서 제공하며 구체적인 요청·응답은 [API 규약](docs/api-conventions.md)을 따른다.
회사별 이력은 `/companies/{company_id}/logs`, 로그 단건은 `/company-logs/{log_id}`에서 조회한다. 삭제한 회사도 원래 UUID로 이력을 조회할 수 있다. Scalar에는 성공·실패·경계값 예제와 실행 순서가 있으며, 생성 응답의 UUID와 목록 응답의 cursor를 복사해 테스트한다.
모델별 이력은 `/models/{model_id}/logs`, 로그 단건은 `/model-logs/{log_id}`에서 동일하게 조회한다.
Brand CRUD는 `/brands`, 이력 목록은 `/brands/{brand_id}/logs`, 로그 단건은 `/brand-logs/{log_id}`에서 제공한다. Brand는 Company·Model과 독립된 차원이며 [Brand](docs/features/dimension/brand.md)·[BrandLog](docs/features/dimension/brand-log.md)의 규칙을 따른다.
Country CRUD는 `/countries`, 국가별 이력은 `/countries/{country_id}/logs`, 로그 단건은 `/country-logs/{log_id}`에서 제공한다. Country는 국가명을 공백 제거·대문자·NFC 정규화 후 유일하게 저장하며, 영문 3자 코드를 직접 입력해야 한다. 자동 생성은 제공하지 않는다. 세부 규칙은 [Country](docs/features/dimension/country.md)·[CountryLog](docs/features/dimension/country-log.md)를 따른다.
Category CRUD는 `/categories`, 분류별 이력은 `/categories/{category_id}/logs`, 로그 단건은 `/category-logs/{log_id}`에서 제공한다. 이름은 공백 제거·대문자·NFC 정규화 후 유일하며 코드는 영문·숫자 3자로 직접 입력하거나 이름에서 자동 생성한다. 코드 변경은 금지하며 삭제 후에도 이력을 보존한다. [Category](docs/features/dimension/category.md)·[CategoryLog](docs/features/dimension/category-log.md)를 따른다.
Year CRUD는 `/years`, 대상별 이력은 `/years/{year_id}/logs`, 로그 단건은 `/year-logs/{log_id}`에서 제공한다. 제품 출시 연도를 JSON 정수로 입력하면 코드를 자동 생성하며 수정 시 코드도 함께 바뀐다. 목록과 이력은 내림차순이다. 구체 규칙은 [Year](docs/features/dimension/year.md)·[YearLog](docs/features/dimension/year-log.md), HTTP 계약은 [API 규약](docs/api-conventions.md#yearyearlog-http-계약)을 따른다.
`make up`은 PostgreSQL 준비 → 일회성 `migrate` 서비스의 Alembic 적용 → API 시작 순서로 실행한다. 마이그레이션 실패 시 API 시작을 막는다.
`0005_merge_brand_country`는 기존 Brand(`0004`)·Country(`0004_country`) 리비전을 병합한다. Category(`0006_category`)·Year(`0006_year_dimension`)는 이 리비전에서 갈라지며 `0007_merge_category_year`로 다시 연결해 최종 단일 head를 유지한다. Category 또는 Year만 적용된 DB에서도 다른 차원을 추가한다. 어느 한쪽만 적용된 DB도 `make up`으로 빠진 차원을 추가하며 기존 데이터·이력을 보존한다.

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
| `make format` | 로컬 uv 환경에서 import 정렬·코드 포맷 적용 |
| `make test-unit` | 로컬 uv 환경에서 DB 없는 단위 테스트 |
| `make test-stop` | 테스트 PostgreSQL 종료, 임시 데이터 폐기 |
| `make check-container` | 컨테이너에서 Ruff 린트·포맷 및 Pyrefly 타입 검사. 타입 진단은 경고부터 실패로 처리 |
| `make compose-check` | Compose 설정 검증 |
| `make ps` | 서비스 상태 확인 |
| `make logs` | 로그 보기. Ctrl+C로 로그 보기만 종료 |
| `make down` | 컨테이너 종료·삭제. PostgreSQL 데이터 볼륨 유지 |

테스트는 `test` Compose 프로필의 `postgres-test` 서비스와 `mdm_test` DB를 사용한다. 개발 DB와 볼륨을 공유하지 않으며, 테스트 시작마다 테스트 테이블을 비운다. 테스트 DB 이름이 다르면 실행을 거부한다. tmpfs 데이터는 테스트 DB 종료 시 사라지며 테스트가 끝나도 서비스는 `make test-stop` 전까지 실행된다.

로컬 `make format`은 import 정렬과 Ruff 포맷을 적용한다.

컨테이너 내부 원시 진입점은 `make migrate`, `make migration-check`, `make test`이며 일반 실행은 위 컨테이너 명령을 사용한다. 테스트는 pytest·pytest-asyncio·HTTPX를 사용한다. Alembic은 런타임 마이그레이션 도구이며 패키지 버전은 설정·잠금 파일에서 관리한다.

## 설정

포트나 DB 설정을 바꾸려면 [.env.example](.env.example)을 `.env`로 복사해 수정한다. 기본 자격증명은 로컬 개발 전용이다.
PostgreSQL은 볼륨에 데이터를 보존하며, 기존 볼륨의 DB 계정·암호는 `.env` 수정만으로 바뀌지 않는다. Redis 캐시는 영속화하지 않는다. Company·Model·Brand·Country·Category·Year 삭제는 물리 삭제지만 전용 `company_logs`·`model_logs`·`brand_logs`·`country_logs`·`category_logs`·`year_logs`에 원본 UUID를 FK 없이 보존하며 이력은 자동 만료하지 않는다.
`CURSOR_SIGNING_KEY`는 최소 32바이트이며 직접 앱을 실행할 때 반드시 설정한다. Compose에는 로컬 개발용 기본값이 있고 키 교체 시 기존 cursor는 무효화된다.

| 파일 | 관리 대상 |
| --- | --- |
| [.python-version](.python-version) | Python 실행 버전 |
| [pyproject.toml](pyproject.toml) | Python 지원 범위·직접 의존성·개발 도구 설정 |
| [uv.lock](uv.lock) | 전체 Python 의존성 잠금 |
| [Dockerfile](Dockerfile) | uv 버전·앱 이미지 구성 |
| [compose.yaml](compose.yaml) | 서비스 설정·PostgreSQL 및 Redis 이미지 버전 |
| [alembic.ini](alembic.ini), [초기 스키마](migrations/versions/0001_company_dimension.py)·[Company 로그 분리](migrations/versions/0002_split_company_logs.py)·[Model 추가](migrations/versions/0003_model_dimension.py)·[Brand 추가](migrations/versions/0004_brand_dimension.py)·[Country 추가](migrations/versions/0004_country_dimension.py)·[Brand·Country 병합](migrations/versions/0005_merge_brand_country.py)·[Category 추가](migrations/versions/0006_category_dimension.py)·[Year 추가](migrations/versions/0006_year_dimension.py)·[Category·Year 병합](migrations/versions/0007_merge_category_year.py) | DB 마이그레이션 설정·스키마 이력 |
| [app.py](src/mdm_demo/app.py) | Scalar 번들 버전 |

## 관련 문서

- [서비스 기능맵](docs/features/README.md)
- [기능 문서 템플릿](docs/templates/feature.md)
- [개발·아키텍처·리뷰 규칙](AGENTS.md)
- [API 규약](docs/api-conventions.md)

기능맵에는 구현 전 합의한 업무 규칙도 포함하며, 해당 문서에 구현 전 요구사항임을 표시한다.

Model은 Company와 독립된 제품 모델 차원입니다. 입력 규칙·이력 정책은 [Model](docs/features/dimension/model.md)과 [ModelLog](docs/features/dimension/model-log.md), HTTP 계약은 기존 [API 규약](docs/api-conventions.md)을 따릅니다.

## 프로젝트 스킬

[explain-diff-html](.agents/skills/explain-diff-html/SKILL.md)은 코드 변경·브랜치·커밋 기록을 배경, 핵심 예시, 코드 흐름, 대화형 퀴즈로 설명하는 프로젝트 스킬이다. 이 저장소의 Codex 대화에서 `$explain-diff-html main의 커밋 기록을 처음 보는 사람에게 설명해 줘`처럼 요청한다. 설치 후 다음 턴부터 사용할 수 있다.

기본 독자는 주니어 백엔드 개발자다. Cursor 기반 페이지네이션·UoW·트랜잭션처럼 적합한 기술 용어를 제목과 본문에 사용하고, 처음 등장할 때 정의·구현 코드·구체적인 예시를 연결해 설명한다.

[Geoffrey Litt의 Gist](https://gist.github.com/geoffreylitt/a29df1b5f9865506e8952488eac3d524)의 HTML 버전을 바탕으로, 관계·상태 변화·데이터 흐름을 실제 도식으로 보여 주도록 보강했다. 탭이나 버튼으로 설명 문구만 교체하는 UI는 시각화를 대신하지 않는다. 원본 기준 리비전은 `126e7fe9eecaafadfe1ac8bb183d135812b608f2`이며 Notion 버전은 포함하지 않는다. 결과물은 CSS·JavaScript를 포함한 단일 HTML로, 저장소 밖에 `YYYY-MM-DD-`로 시작하는 파일명으로 저장한다.
