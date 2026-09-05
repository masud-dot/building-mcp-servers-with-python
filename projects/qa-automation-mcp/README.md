# QA Automation MCP Server

A server that reports on test runs from an external API, serves artefacts from
a jailed directory, and runs diagnostics without giving anybody a shell.

**Needs nothing but Python.** The upstream API is a stub that ships with the
project, and the test suite does not even need that.

## What you'll build

Tools that call an external HTTP API with bounded retries and a mapped failure
taxonomy; resources that serve files from a directory nobody can escape; and a
subprocess runner that takes a suite name rather than a command.

## What you'll learn

- How to keep HTTP out of your tool layer entirely
- What each upstream failure should look like to a caller
- Why `safe_join` catches a symlink that the SDK's own path checks do not
- Why an argument vector makes command injection inexpressible rather than
  merely detected
- How to build a test suite that runs with nothing available

## Installation

```bash
uv sync
cp .env.example .env
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `QAOPS_BASE_URL` | `http://127.0.0.1:8931` | Test-management API |
| `QAOPS_TOKEN` | — | API token, held as `SecretStr` |
| `QAOPS_ARTIFACT_ROOT` | `./artifacts` | The jail. Nothing outside is served |
| `QAOPS_MAX_ARTIFACT_BYTES` | 65536 | Read cap, minimum 1024 |
| `QAOPS_MAX_RETRIES` | 2 | Retries for 502, 503 and 504 only |

## Running

```bash
# terminal 1 — the stub upstream
uv run python stub/api.py

# terminal 2
uv run python -m qaops
```

## Testing

```bash
uv run pytest -q          # 20 passed
```

**This suite runs with nothing available** — no network, no database, no stub.
Every upstream is an `httpx2.MockTransport` and every filesystem is a pytest
`tmp_path`. Stop the stub and run it again to confirm.

```text
tests/failure/     six upstream failures, each asserting the caller's message
tests/security/    one test per control that leaves no trace in the schema
tests/test_regressions.py   one test per defect that reached a running system
```

## Security notes

**`insecure/` contains deliberately vulnerable code.** It is the "before" half
of Chapter 23 — command injection through a shell string, and SSRF through a
caller-supplied URL. Nothing in `src/` imports it. Do not run it outside a
sandbox.

The working server:

- Runs only diagnostics from a fixed registry, via an argument vector, with a
  replaced environment so no credential reaches the child process
- Serves only files beneath the artefact root, with symlinks excluded from the
  index and refused on read
- Refuses any endpoint outside an origin allow-list, re-checking every redirect
  hop and rejecting names that resolve to private addresses
- Reveals nothing in refusals: the gate that fired goes to the log

## Project structure

```text
README.md
insecure
insecure/README.md
insecure/check_endpoint.py
insecure/run_tests.py
pyproject.toml
src
src/qaops
src/qaops/__init__.py
src/qaops/__main__.py
src/qaops/config.py
src/qaops/models.py
src/qaops/resources
src/qaops/resources/__init__.py
src/qaops/resources/artifacts.py
src/qaops/server.py
src/qaops/services
src/qaops/services/__init__.py
src/qaops/services/artifacts.py
src/qaops/services/execution.py
src/qaops/services/fetching.py
src/qaops/services/testruns.py
src/qaops/tools
src/qaops/tools/__init__.py
src/qaops/tools/runs.py
stub
stub/api.py
tests
tests/__init__.py
tests/conftest.py
tests/failure
tests/failure/__init__.py
tests/failure/test_no_leaks.py
tests/failure/test_upstream.py
tests/security
tests/security/__init__.py
tests/security/test_boundaries.py
tests/test_regressions.py
verify.py
```

## Related book chapters

Chapters 13, 14, 15, 21 and 23.
