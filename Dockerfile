FROM ghcr.io/astral-sh/uv:0.11.23-debian-slim

RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY .python-version pyproject.toml uv.lock ./
RUN uv sync --locked && rm -rf /tmp/uv-cache

RUN useradd --create-home --uid 10001 app && chown -R app:app /app
COPY --chown=app:app src ./src
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app Makefile alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app tests ./tests
USER app

EXPOSE 8000
CMD ["uv", "run", "--locked", "uvicorn", "mdm_demo.app:app", "--host", "0.0.0.0", "--port", "8000"]
