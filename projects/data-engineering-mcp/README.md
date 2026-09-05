# Data Engineering MCP Server

A read-only warehouse server that grows, across nine chapters, into a
production deployment: authenticated, scope-checked, horizontally scalable,
rate-limited and observable.

**Requires PostgreSQL.**

## What you'll build

Tools that query a warehouse without ever accepting SQL; one destructive
operation guarded by a typed confirmation and a scope; long-running scans
addressed by handle so any instance can answer; and the operational layer that
makes three instances behind a load balancer work.

## What you'll learn

- Why an allow-list beats sanitising, and why the grant matters more than both
- How to ask a user something when the protocol forbids the server from asking
- What OAuth resource-server verification actually involves
- Why a handle beats hidden session state
- How cache scope becomes an access-control decision

## Prerequisites

Python 3.10+ and PostgreSQL 14 or later (16 was used).

## Installation

```bash
uv sync
docker compose up -d warehouse
psql "$DATAENG_DSN" -f sql/001-schema.sql
cp .env.example .env
```

## Database setup

Read `sql/001-schema.sql` before running it. **The grants are the security
boundary**, and this file is where that boundary is defined:

| Role | May | May not |
|---|---|---|
| `mcp_reader` | `SELECT` on three analytics tables | Write anything. Read `api_credentials` |
| `mcp_writer` | `DELETE` from `pipeline_runs`; write scan results | Read `api_credentials`. Touch any other table |

`analytics.api_credentials` exists specifically to prove the boundary. Neither
role can read it. Verify:

```bash
PGPASSWORD=localdev psql -h 127.0.0.1 -U mcp_reader -d warehouse \
  -c "delete from analytics.pipeline_runs;"
# expected: ERROR: permission denied for table pipeline_runs
```

Both roles ship with the password `localdev`, which is fine on a laptop and
not fine anywhere else. Change it in `sql/001-schema.sql` and `.env` together.

## Configuration

| Variable | Purpose |
|---|---|
| `DATAENG_DSN` | Read-only connection. Held as `SecretStr` |
| `DATAENG_WRITER_DSN` | The one write path. Separate credential on purpose |
| `DATAENG_MAX_ROWS` | Row cap, 1–1000 |
| `DATAENG_STATEMENT_TIMEOUT_MS` | Per-statement timeout |
| `DATAENG_AUTH_ENABLED` | Must be true for any HTTP deployment |
| `DATAENG_AUTH_ISSUER` / `_AUDIENCE` / `_PUBLIC_KEY` | Token verification |

## Running

```bash
uv run python -m dataeng                 # stdio
DATAENG_AUTH_ENABLED=true uv run python -m dataeng http
```

Over HTTP the process **refuses to start** without a token verifier. That is
deliberate: a server whose auth capability has been switched off should not
serve a network.

Three instances behind a balancer, as in Chapter 26:

```bash
DATAENG_PORT=8101 uv run python -m dataeng http &
DATAENG_PORT=8102 uv run python -m dataeng http &
DATAENG_PORT=8103 uv run python -m dataeng http &
uv run python ../../scripts/roundrobin.py 8100 8101 8102 8103
```

## Testing

```bash
uv run pytest -q                      # 27 passed  (needs PostgreSQL)
uv run pytest -m "not integration"    # 9 passed, 18 deselected  (no database)
```

Tests that open the server lifespan need the database, because the lifespan
opens a connection pool. They are marked `integration` automatically.

Accepting a deliberate contract change:

```bash
uv run python -m tests.contract.refresh
```

Then read the diff before committing it. That is the point of the snapshot.

## Documentation

- [`docs/threat-model.md`](docs/threat-model.md) — twelve threats, three open,
  with the deployment scope stated
- [`docs/runbook.md`](docs/runbook.md) — for whoever is on call, including a
  "what not to do" section

## Security notes

Five independent layers guard the read path: schema constraints, a table
allow-list, composed identifiers, row caps with statement timeouts, and the
database grant. The destructive operation adds a typed confirmation and a
scope check, on a credential that can delete from exactly one table.

Secrets are `SecretStr`, so they do not appear in `repr`, JSON, tracebacks or
logs. Refusal messages name what *is* available and never why a check fired.

## Project structure

```text
Dockerfile
compose.yaml
docs
docs/runbook.md
docs/threat-model.md
pyproject.toml
sql
sql/001-schema.sql
src
src/dataeng
tests
tests/__init__.py
tests/conftest.py
tests/contract
tests/test_auth.py
tests/test_compatibility.py
verify.py
verify_mrtr.py
```

## Related book chapters

Chapters 12, 15, 18, 20, 22, 24, 26, 27, 28.
