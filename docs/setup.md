# Setup

Everything here was tested on Linux with Python 3.12. Notes for macOS and
Windows are included where behaviour differs.

## 1. Python

Python 3.10 or later. 3.12 is what the book uses.

```bash
python --version
```

On Windows use `py -3.12` if you have several versions installed.

## 2. uv (recommended)

The projects use [uv](https://docs.astral.sh/uv/) for environments and
lockfiles. It is not required, but it is what the book's commands assume.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Without uv, every project also works with `venv` and `pip`:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 3. Verify your environment

Run this before anything else:

```bash
cd scripts
uv run --with "mcp==2.1.1" python verify_versions.py
```

It checks the Python version, the installed SDK, the protocol revision, and
performs one live in-memory round trip. It exits non-zero on any mismatch and
names what failed.

## 4. Install a project

Each project is independent.

```bash
cd projects/productivity-mcp
uv sync
uv run pytest -q
uv run python -m productivity
```

## 5. PostgreSQL

Needed by `data-engineering-mcp` and the capstone only.

### With Docker (simplest)

```bash
cd projects/data-engineering-mcp
docker compose up -d warehouse
```

### With a local PostgreSQL

PostgreSQL 14 or later. The book used 16.

```bash
createdb warehouse
psql -d warehouse -f sql/001-schema.sql
```

The schema file creates two roles with deliberately different grants:

| Role | May | May not |
|---|---|---|
| `mcp_reader` | `SELECT` on three tables | Write anything; read the credentials table |
| `mcp_writer` | `DELETE` from one table; write scan results | Read the credentials table; touch any other table |

**Change the passwords.** The schema ships with `CHANGE_ME` placeholders. Put
the real values in `.env`, which is git-ignored.

Verify the grants took effect — this is the security boundary the whole
project rests on, and it is worth seeing refuse:

```bash
PGPASSWORD=<reader-password> psql -h 127.0.0.1 -U mcp_reader -d warehouse \
  -c "delete from analytics.pipeline_runs;"
# expected: ERROR: permission denied for table pipeline_runs
```

The capstone uses the same pattern with its own roles; see
`capstone/production-ai-operations-mcp/sql/001-schema.sql`.

## 6. Configuration

```bash
cp .env.example .env
```

Then edit `.env`. Every value in `.env.example` is a placeholder. Settings are
validated at startup, so a typo in a variable name produces a clear error
rather than a silent default.

## 7. Stub services

Two projects include small stand-in HTTP services so nothing depends on a
vendor account:

```bash
# QA Automation — a test-management API
cd projects/qa-automation-mcp && uv run python stub/api.py

# Capstone — a monitoring API
cd capstone/production-ai-operations-mcp && uv run python stub/monitoring.py
```

The test suites do **not** need these running; they inject a mock transport
instead. The stubs are for running the servers by hand.

## Platform notes

**Windows.** Use `py -3.12` and `.venv\Scripts\activate`. Path examples in the
book use forward slashes; Python accepts them on Windows. The filesystem jail
in Chapter 14 uses `O_NOFOLLOW`, which is a no-op on Windows — the containment
check still works, but the symlink race window is wider.

**macOS.** No differences. If PostgreSQL was installed via Homebrew, the
default superuser is your own username rather than `postgres`.

**Linux.** No differences. Starting PostgreSQL varies by distribution;
`pg_ctlcluster 16 main start` on Debian and Ubuntu.
