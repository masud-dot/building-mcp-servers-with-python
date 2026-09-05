# Building MCP Servers with Python — Companion Repository

Every project, example and test from the book *Building MCP Servers with Python: A Practical Guide to Model Context Protocol, Tools, Resources, Prompts, Security, Testing, and Production AI Integrations*.

Everything here was executed against the versions below before publication. If something does not work, that is a defect worth reporting rather than something you are doing wrong.

---

## Baseline

| | Version |
|---|---|
| **MCP specification** | **2026-07-28** |
| **MCP Python SDK** | **`mcp==2.1.1`** (pinned exactly, not a range) |
| **Python** | **3.12** primary; 3.10–3.14 supported |
| Server class | `MCPServer`, from `mcp.server.mcpserver` |
| Transports | stdio, Streamable HTTP |

The pin is exact on purpose. The SDK crossed a major version in July 2026, and code written for one major does not run on the other — Chapter 5 of the book explains what happens if you use a range instead.

`FastMCP` was the server class in the SDK's 1.x line and is now `MCPServer`. A separate, independent third-party project is also called FastMCP; it is not used here. Chapter 31 distinguishes them.

---

## Who this is for

Python developers building MCP servers that other people will depend on. You should be comfortable writing a function with type hints and managing a virtual environment. No prior MCP or async knowledge is assumed.

---

## Quick start

```bash
# 1. Get the code
git clone https://github.com/masud-dot/building-mcp-servers-with-python building-mcp-servers-with-python
cd building-mcp-servers-with-python

# 2. Check your environment matches the book
cd scripts && uv run --with "mcp==2.1.1" python verify_versions.py

# 3. Pick a project and install it
cd ../projects/productivity-mcp
uv sync

# 4. Run its tests
uv run pytest -q

# 5. Run the server
uv run python -m productivity
```

Step 2 should print `Environment matches the book.` If it does not, it will tell you exactly which assumption failed. See [`docs/troubleshooting.md`](docs/troubleshooting.md).

Every project is independent, with its own `pyproject.toml` and its own virtual environment. There is no repository-wide install step.

### If you do not have `uv`

`uv` is used throughout because it is fast and its lockfiles are reproducible. Standard tooling works too:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

---

## What is here

```text
building-mcp-servers-with-python/
├── README.md
├── LICENSE
├── .gitignore
│
├── docs/
│   ├── setup.md                    environment, PostgreSQL, per-platform notes
│   ├── troubleshooting.md          real errors and what they mean
│   ├── architecture.md             how the projects are layered
│   └── chapter-project-map.md      every chapter to its code
│
├── scripts/
│   ├── verify_versions.py          the tripwire; run this first
│   ├── inspect_wire.py             a proxy that logs raw MCP traffic
│   ├── roundrobin.py               a balancer for the Chapter 26 demonstration
│   └── traces/                     captured exchanges, both protocol eras
│
├── projects/
│   ├── productivity-mcp/           Part II — tools, resources, prompts, tests
│   ├── data-engineering-mcp/       Parts III, VI, VII — database, auth, production
│   └── qa-automation-mcp/          Parts III, V, VI — API, filesystem, security
│
├── capstone/
│   └── production-ai-operations-mcp/   Chapter 32 — all of it, in one server
│
├── chapter-projects/               standalone examples for single chapters
│   ├── 05-setup/  06-first-server/  16-client/
│   ├── 17-multi-server/  29-extensions/  30-long-running/
│
└── migration/                      a v1 server and its v2 equivalent
```

---

## The projects

| Project | Chapters | What it demonstrates | Needs |
|---|---|---|---|
| [**productivity-mcp**](projects/productivity-mcp/) | 6–11, 19, 25 | Tools, structured output, resources, prompts, lifespan state, a fast test suite, both transports | Python only |
| [**data-engineering-mcp**](projects/data-engineering-mcp/) | 12, 15, 18, 20, 22, 24, 26–28 | PostgreSQL with two roles, confirmed destructive write, OAuth scopes, horizontal scale, caching, rate limiting, observability | PostgreSQL |
| [**qa-automation-mcp**](projects/qa-automation-mcp/) | 13–15, 21, 23 | External API integration, filesystem jail, subprocess execution, failure injection, and a deliberately vulnerable variant | Python only |
| [**production-ai-operations-mcp**](capstone/production-ai-operations-mcp/) | 32 | Eight tools, three resources, two prompts, two database roles, jailed filesystem, diagnostic registry, confirmed write, handles, cache hints, rate limiting, structured logging, per-tool metrics | PostgreSQL |

Start with **productivity-mcp**. It needs nothing but Python and it is where the book starts.

---

## Tests

**84 tests across the four projects.** Two projects need PostgreSQL and two do not, and the repository is explicit about which:

| Project | `pytest -q` | `pytest -m "not integration"` | Needs a database |
|---|---|---|---|
| productivity-mcp | 20 passed | — | No |
| qa-automation-mcp | 20 passed | — | No |
| data-engineering-mcp | 27 passed | 9 passed, 18 deselected | Yes, for the 18 |
| production-ai-operations-mcp | 17 passed | 8 passed, 9 deselected | Yes, for the 9 |

Tests that open a server lifespan need PostgreSQL, because the lifespan opens a connection pool. They are marked `integration` automatically. To run only what works without a database:

```bash
uv run pytest -m "not integration"
```

The QA Automation suite is the one to look at if you want to see how a suite runs with **nothing** available — no network, no database, no external service. Every upstream there is an injected transport and every filesystem is a temporary directory. Chapter 21 explains the technique.

---

## PostgreSQL

Two projects need it. Each ships a `compose.yaml`:

```bash
cd projects/data-engineering-mcp
docker compose up -d warehouse
psql "$DATABASE_URL" -f sql/001-schema.sql
```

The schema file creates the roles, the grants and the seed data. Read it before running it — in both database projects the **grants are the security boundary**, and the schema is where that boundary is defined. Full instructions in [`docs/setup.md`](docs/setup.md).

---

## Configuration

No project contains a real credential. Each ships a `.env.example` with obvious placeholders:

```bash
cp .env.example .env
# then edit .env with your own values
```

`.env` is in `.gitignore`. Every setting is validated at startup with a typed model, and secrets are held as `SecretStr` so they do not appear in logs, tracebacks or JSON output.

---

## A note on the `insecure/` directory

`projects/qa-automation-mcp/insecure/` contains **deliberately vulnerable code**. It exists to be broken — it is the "before" half of Chapter 23, and nothing in the working server imports it.

Do not run it outside a sandbox. If you find that directory in a deployment, that is the finding.

---

## Chapter to code

[`docs/chapter-project-map.md`](docs/chapter-project-map.md) maps every chapter to the exact files and tests it uses.

---

## Problems

If a command in the book does not work, or a test fails on a clean machine, please open an issue. Include your operating system, your Python version, and the output of `scripts/verify_versions.py` — that script exists precisely to make these reports quick to diagnose.

---

## Licence

Code: MIT, see [LICENSE](LICENSE). The text of the book is separately copyrighted.
