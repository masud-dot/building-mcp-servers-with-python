# Build and run the data engineering MCP server.
FROM python:3.12-slim AS base

# uv, for the same lockfile the developers use.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so a source change does not reinstall
# them. uv.lock is committed, so this layer is reproducible.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Not root. The server reads a database and a config file and
# needs nothing else.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin mcp
USER 10001

# Configuration is injected, never baked in. There is no .env
# in this image and no default credential.
ENV AIOPS_AUTH_ENABLED=true \
    AIOPS_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Refuses to start without a token verifier. Chapter 24.
CMD ["uv", "run", "--no-dev", "python", "-m", "aiops", "http"]
