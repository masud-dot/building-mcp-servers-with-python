# Troubleshooting

Real errors from this repository, and what each one means. Every message here
was produced by running the code.

## `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`

```text
This is mcp 2.x, where FastMCP was renamed to MCPServer
(from mcp.server.mcpserver import MCPServer) and other APIs changed
```

You are running v1-era code on the v2 SDK. The SDK raises this deliberately
rather than a bare import error. Either migrate the code (Chapter 31 and
`migration/` show the six changes) or pin `mcp>=1.28,<2` if you are not ready.

## `ValidationError: Invalid JSON: expected value at line 1 column 1`

Something wrote to standard output while the server was running over stdio.
Under that transport **stdout is the protocol** — one stray `print()` breaks
the connection.

Send diagnostics to stderr instead:

```python
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
```

Three sources catch people: your own `print`, a library that prints on import,
and a subprocess launched with stdout inherited rather than piped.

## `Bad Request: Missing session ID`

Misleading. There are no sessions in the 2026-07-28 protocol. You sent an HTTP
request with no `MCP-Protocol-Version` header, or one naming a handshake-era
revision, so the server routed it to the old code path — which does need a
session, does not find one, and says so.

Add the header:

```text
MCP-Protocol-Version: 2026-07-28
```

## `mcp-name header does not match the request body's 'name' parameter`

A `tools/call` over HTTP needs both `Mcp-Method: tools/call` and
`Mcp-Name: <tool>`, and both must agree with the body. This is what lets a
gateway route without parsing the body.

## `PoolTimeout: pool initialization incomplete after 5.0 sec`

PostgreSQL is not reachable. The pools open with `timeout=5.0` so this fails
in seconds; without it the pool waits on its own default and a missing
database looks like a hang. Start it, or run only the tests that do not need
it:

```bash
uv run pytest -m "not integration"
```

## `permission denied for table ...`

Usually correct behaviour rather than a fault. The database roles are
deliberately narrow — the reader role cannot write, and neither role can read
the credentials table. If you hit this from a tool that should work, check
which role your `.env` points at.

## `RuntimeError: Attempted to exit cancel scope in a different task`

You are using `pytest-asyncio`. The SDK is built on **anyio**, whose cancel
scopes must be entered and exited in the same task, and `pytest-asyncio` runs
async fixtures in a different task from the test.

Use anyio's plugin instead:

```toml
[tool.pytest.ini_options]
markers = ["anyio"]
```

```python
pytestmark = pytest.mark.anyio

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
```

Simple tests without async fixtures pass under `pytest-asyncio`, which is why
this hides until you write your first fixture.

## `ModuleNotFoundError: No module named 'tests'`

You ran a script inside `tests/` directly. Run it as a module from the project
root instead:

```bash
uv run python -m tests.contract.refresh
```

## `Rate limit exceeded. Wait a few seconds and try again.`

The limiter is real. In a test suite, tests share one bucket, which makes the
suite order-dependent. Reset it between tests:

```python
@pytest.fixture(autouse=True)
def fresh_limiter():
    limiter._buckets.clear()
    yield
    limiter._buckets.clear()
```

## `Refusing to serve over HTTP without authentication`

By design. A server with an authentication capability that has been switched
off will not start over HTTP. Set `AUTH_ENABLED=true` and supply a public key,
or use stdio.

## `Address already in use`

Another process holds the port. Find it with `lsof -i :8000` (macOS, Linux) or
`netstat -ano | findstr :8000` (Windows), or pass `--port`.

## `extra_forbidden` on startup

A `.env` key does not match any setting. The models use `extra="forbid"` so a
typo fails loudly rather than being ignored.

Note the asymmetry: this catches typos in `.env` but **not** in real
environment variables, which is why the projects also warn about unrecognised
`*_`-prefixed variables at startup.

## Tests pass individually but fail together

Shared state. The usual culprits are the rate limiter (above) and module-level
data that should be in the lifespan. Each project has an isolation test
asserting that a new connection sees fresh state — if that one fails, fix it
first.

## `uv: command not found`

Either install uv (see `setup.md`) or use `venv` and `pip`; every project
works with both.

## Still stuck

Run `scripts/verify_versions.py` and include its output in an issue. It names
the exact assumption that failed.
