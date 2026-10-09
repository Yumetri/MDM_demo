"""Read-only connectivity check, executed inside the API container."""

import asyncio
import os
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


def main() -> None:
    with urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
        if response.status != 204:
            raise RuntimeError("API liveness check failed")
    asyncio.run(check_dependencies())
    print("OK: API /health, PostgreSQL SELECT 1, Redis PING")


if __name__ == "__main__":
    main()
