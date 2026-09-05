# Production AI Operations MCP Server

The capstone. A server an on-call engineer's assistant can use to investigate
an incident, with tight limits on what it may change.

**Requires PostgreSQL.**

## What it does

| | |
|---|---|
| **Tools** | `list_services`, `get_service_health`, `query_incidents`, `get_deployment_history`, `run_diagnostic`, `start_log_scan`, `get_scan_result`, `acknowledge_incident` |
| **Resources** | `catalogue://services`, `incident://{incident_id}`, `service://{name}/runbook` |
| **Prompts** | `investigate_incident`, `postmortem_draft` |

Eight tools, three resources, two prompts, twenty-two source files. One tool
changes anything.

## Architecture

```text
transport        stdio or Streamable HTTP, host and origin validated
middleware       per-tool metrics, per-caller rate limiting
authentication   bearer token: signature, issuer, audience, expiry
tool layer       schemas, scope checks, no I/O
service layer    database, monitoring API, filesystem jail, subprocess
credentials      two database roles, an API token, a jailed root
```

## Grants before code

The database roles are created and **verified before any Python is written**.
That ordering is the chapter's argument: security is an architectural input,
not something added afterwards.

```sql
GRANT SELECT ON ops.services, ops.incidents, ops.deployments,
                ops.scan_results TO aiops_reader;

-- Writes exactly two things and nothing else.
GRANT SELECT, UPDATE ON ops.incidents TO aiops_writer;
GRANT SELECT, INSERT, UPDATE ON ops.scan_results TO aiops_writer;
```

`ops.oncall_pager_tokens` holds a live-looking credential and is granted to
**neither** role. Prove it before trusting anything above it:

```bash
PGPASSWORD=localdev psql -h 127.0.0.1 -U aiops_writer -d aiops \
  -c "select * from ops.oncall_pager_tokens;"
# expected: ERROR: permission denied for table oncall_pager_tokens

PGPASSWORD=localdev psql -h 127.0.0.1 -U aiops_reader -d aiops \
  -c "update ops.incidents set status='x';"
# expected: ERROR: permission denied for table incidents
```

## Installation

```bash
uv sync
docker compose up -d aiops-db
psql "$AIOPS_DSN" -f sql/001-schema.sql
cp .env.example .env
```

## Running

```bash
uv run python -m aiops                    # stdio
AIOPS_AUTH_ENABLED=true uv run python -m aiops http
```

HTTP refuses to start without a token verifier.

The monitoring stub, if you want to exercise `get_service_health` by hand:

```bash
uv run python stub/monitoring.py
```

## Testing

```bash
uv run pytest -q                      # 17 passed  (needs PostgreSQL)
uv run pytest -m "not integration"    # 8 passed, 9 deselected  (no database)
```

Seventeen tests, one per boundary. Each names the control it defends:

```python
def test_runbook_symlink_escape_is_refused(tmp_path):
    """Only safe_join catches this."""
```

## Threat model

**Trust boundaries.** User to host (the host's consent policy, not ours);
host to server (tool arguments, all untrusted); server to backing systems
(bounded by credentials); and the return path, where everything the server
emits enters a context that acts.

**Authorisation.** Two scopes. `ops:read` grants the six investigation tools;
`ops:write` grants only `acknowledge_incident`. Scopes and grants are
independent layers — if the scope check were wrong, the grant still bounds the
damage.

**Least privilege.** Two roles, neither able to read the credentials table.
The writer can update one table and insert scan results.

**Filesystem.** Runbooks are served only from beneath one root, resolved with
`safe_join`, opened with `O_NOFOLLOW`, with symlinks excluded from the index.
Refusals do not disclose the root.

**External API.** One fixed host from configuration, redirects disabled,
bounded retries for 502/503/504 only, and every failure mapped to a message a
caller can act on.

**Execution.** Diagnostics come from a fixed registry, run through an argument
vector with no shell, in a pinned working directory, with the environment
**replaced** rather than inherited — the parent's environment holds every
credential this server has.

**Rate limiting.** Per caller identity, charged by the work a call causes:
listing costs 1, a diagnostic costs 15. The bucket table is bounded so a flood
of identities cannot exhaust memory.

**Secrets.** All held as `SecretStr`. Verified absent from `repr`,
`model_dump_json`, exception messages and structured logs, where a field-name
denylist redacts `token`, `password`, `dsn`, `authorization` and `secret`.

**Logging.** JSON on stderr, never stdout. Each line carries `trace_id`, so a
log line and a trace are the same investigation.

**Errors.** Detail to the log, a usable sentence to the caller. A refusal
never names the gate that fired.

## Known limitations

Stated rather than hidden:

- **No row-level authorisation.** `ops:read` grants every incident to every
  caller. Restricting by team needs ownership in the data model.
- **Injection is unmitigated.** An incident summary is text somebody wrote and
  it reaches the model. No server can solve this; this one narrows the
  consequence to a single confirmed, scope-gated write.
- **The diagnostics are toys.** Three registry entries that print version
  strings. The mechanism is the lesson.
- **The rate limiter is per instance.** Three instances give three times the
  intended limit. Fixing that needs shared state.

## Project structure

```text
Dockerfile
compose.yaml
pyproject.toml
runbooks
runbooks/checkout.md
sql
sql/001-schema.sql
src
src/aiops
stub
stub/monitoring.py
tests
tests/__init__.py
tests/conftest.py
tests/test_capstone.py
```

## Related book chapters

Chapter 32, drawing on every part of the book.
