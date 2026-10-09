"""Read-only connectivity check, executed inside the API container."""

import asyncio
import json
import os
from urllib.error import HTTPError
from urllib.request import urlopen

from redis.asyncio import Redis
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_dependencies() -> None:
    url = URL.create(
        "postgresql+asyncpg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )
    engine = create_async_engine(url, connect_args={"timeout": 5})
    try:
        async with asyncio.timeout(10):
            async with engine.connect() as connection:
                result = await connection.scalar(text("SELECT 1"))
                if result != 1:
                    raise RuntimeError("PostgreSQL connectivity check failed")
    finally:
        await engine.dispose()

    async with Redis.from_url(os.environ["REDIS_URL"], socket_timeout=5) as redis:
        async with asyncio.timeout(10):
            if not await redis.ping():
                raise RuntimeError("Redis connectivity check failed")


def check_api_docs() -> None:
    with urlopen("http://127.0.0.1:8000/docs", timeout=5) as response:
        html = response.read().decode()
        if "Scalar.createApiReference" not in html or "SwaggerUIBundle" in html:
            raise RuntimeError("/docs must serve Scalar instead of Swagger UI")
        if '"url": "/openapi.json"' not in html:
            raise RuntimeError("Scalar must load the application's OpenAPI schema")

    with urlopen("http://127.0.0.1:8000/openapi.json", timeout=5) as response:
        schema = json.load(response)
        if "204" not in schema["paths"]["/health"]["get"]["responses"]:
            raise RuntimeError("OpenAPI must document the health response")
        if "/docs" in schema["paths"]:
            raise RuntimeError("Documentation UI must not be an OpenAPI operation")

    for path in ("/redoc", "/docs/oauth2-redirect"):
        try:
            with urlopen(f"http://127.0.0.1:8000{path}", timeout=5):
                raise RuntimeError(f"Legacy documentation route is still enabled: {path}")
        except HTTPError as error:
            if error.code != 404:
                raise


def main() -> None:
    with urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
        if response.status != 204:
            raise RuntimeError("API liveness check failed")
    check_api_docs()
    asyncio.run(check_dependencies())
    print("OK: API /health, Scalar /docs, OpenAPI, PostgreSQL SELECT 1, Redis PING")


if __name__ == "__main__":
    main()
