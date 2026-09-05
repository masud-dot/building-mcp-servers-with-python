# Productivity MCP Server

The book's first real server. It manages a task list, and it exists to teach
the four things every MCP server needs: tools, structured results, resources
and prompts.

**Needs nothing but Python.** No database, no external service.

## What you'll build

A server exposing six tools, four resources, two prompts and a completion
handler, with state managed by a lifespan so each connection is independent.
By Chapter 25 it serves over both stdio and Streamable HTTP from one entry
point.

## What you'll learn

- How a Python type hint becomes a JSON Schema the model must satisfy
- Why a result has two channels — text for the model, structured data for code
- The difference between a fixed resource and a resource template
- Why prompts are user-controlled and tools are model-controlled
- How lifespan state makes tests independent of each other

## Prerequisites

Python 3.10 or later; 3.12 recommended.

## Installation

```bash
uv sync
```

Or without uv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

```bash
cp .env.example .env
```

All values have working defaults. Nothing here is secret.

| Variable | Default | Purpose |
|---|---|---|
| `PRODUCTIVITY_MAX_TASKS` | 500 | Cap on tasks held in memory |
| `PRODUCTIVITY_LOG_LEVEL` | INFO | Logging level |

## Running

```bash
# stdio — what a desktop host launches
uv run python -m productivity

# Streamable HTTP — host and origin lists are required
uv run python -m productivity --transport http --port 8020 \
    --allow-host 127.0.0.1:8020 --allow-origin https://app.example
```

The HTTP path warns that this server has no authentication. That is accurate:
authentication arrives in Chapter 24 on a different project. Do not expose
this beyond localhost.

`mounted.py` shows the same server mounted beside ordinary routes in an
existing Starlette application.

## Testing

```bash
uv run pytest -q          # 20 passed
```

No database and no network. Every test connects a client directly to the
server object, which is roughly 136 times faster than launching a subprocess.

Note the plugin: this project uses **anyio's** pytest plugin, not
`pytest-asyncio`. The SDK is built on anyio, and `pytest-asyncio` fails on
teardown of any async fixture. Chapter 19 explains.

## Example

```bash
uv run python verify.py
```

Creates a task, lists tasks, reads a resource and prints what came back.

## Security notes

- Tool arguments are model-generated and therefore untrusted; every one is
  bounded by its schema
- Exception messages are withheld from callers; the detail goes to the log
- Nothing here reaches a network or a filesystem

## Troubleshooting

A `print()` in a handler breaks the stdio connection — stdout is the protocol.
See [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md).

## Project structure

```text
README.md
mounted.py
pyproject.toml
src
src/productivity
src/productivity/__init__.py
src/productivity/__main__.py
src/productivity/config.py
src/productivity/models.py
src/productivity/prompts
src/productivity/prompts/__init__.py
src/productivity/prompts/review.py
src/productivity/resources
src/productivity/resources/__init__.py
src/productivity/resources/notes.py
src/productivity/resources/tasks.py
src/productivity/server.py
src/productivity/store.py
src/productivity/tools
src/productivity/tools/__init__.py
src/productivity/tools/tasks.py
src/productivity/transport.py
tests
tests/conftest.py
tests/test_isolation.py
tests/test_prompts.py
tests/test_resources.py
tests/test_tools.py
verify.py
```

## Related book chapters

Chapters 6–11, 19 and 25.
