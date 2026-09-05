# Chapter to code

Every path below exists in this repository.

## Part I — Fundamentals (1–4)

| Chapter | Code |
|---|---|
| 1 Why MCP Exists | `scripts/verify_versions.py` |
| 2 The MCP Architecture | — conceptual |
| 3 Tools, Resources and Prompts | — conceptual |
| 4 The Wire Protocol | `scripts/inspect_wire.py`, `scripts/traces/` |

## Part II — Building (5–11)

| Chapter | Code |
|---|---|
| 5 Environment and Project Setup | `chapter-projects/05-setup/` |
| 6 Your First MCP Server | `chapter-projects/06-first-server/` |
| 7 Tools I — Parameters | `projects/productivity-mcp/src/productivity/tools/` |
| 8 Tools II — Structured Output | `projects/productivity-mcp/src/productivity/models.py` |
| 9 Resources and Templates | `projects/productivity-mcp/src/productivity/resources/` |
| 10 Prompts | `projects/productivity-mcp/src/productivity/prompts/` |
| 11 Errors, Context and Lifespan | `projects/productivity-mcp/src/productivity/server.py` |

## Part III — Real Integrations (12–15)

| Chapter | Code |
|---|---|
| 12 Database Integration | `projects/data-engineering-mcp/src/dataeng/db.py`, `sql/001-schema.sql` |
| 13 REST API Integration | `projects/qa-automation-mcp/src/qaops/services/testruns.py`, `stub/api.py` |
| 14 Files and Documents | `projects/qa-automation-mcp/src/qaops/services/artifacts.py` |
| 15 Configuration and Secrets | `config.py` in all three projects, `.env.example` |

## Part IV — Clients (16–18)

| Chapter | Code |
|---|---|
| 16 Writing Python MCP Clients | `chapter-projects/16-client/cli.py` |
| 17 Multi-Server Architectures | `chapter-projects/17-multi-server/assistant.py` |
| 18 Multi Round-Trip Requests | `projects/data-engineering-mcp/src/dataeng/tools/pipelines.py` |

## Part V — Testing (19–21)

| Chapter | Code |
|---|---|
| 19 Testing Foundations | `projects/productivity-mcp/tests/` |
| 20 Contract and Compatibility | `projects/data-engineering-mcp/tests/contract/` |
| 21 Negative and Failure Testing | `projects/qa-automation-mcp/tests/failure/`, `tests/security/` |

## Part VI — Security (22–24)

| Chapter | Code |
|---|---|
| 22 The MCP Threat Model | `projects/data-engineering-mcp/docs/threat-model.md` |
| 23 Secure Tool Design | `projects/qa-automation-mcp/src/qaops/services/execution.py`, `fetching.py`, `insecure/` |
| 24 Authentication and Authorisation | `projects/data-engineering-mcp/src/dataeng/auth/` |

## Part VII — Production (25–28)

| Chapter | Code |
|---|---|
| 25 Transports in Production | `projects/productivity-mcp/src/productivity/transport.py`, `mounted.py` |
| 26 Stateless Architecture | `projects/data-engineering-mcp/src/dataeng/state.py`, `scripts/roundrobin.py` |
| 27 Caching and Rate Limiting | `projects/data-engineering-mcp/src/dataeng/ratelimit.py` |
| 28 Observability and Deployment | `projects/data-engineering-mcp/src/dataeng/observability.py`, `health.py`, `Dockerfile`, `docs/runbook.md` |

## Part VIII — Advanced (29–31)

| Chapter | Code |
|---|---|
| 29 The Extensions Framework | `chapter-projects/29-extensions/` |
| 30 Long-Running Work | `chapter-projects/30-long-running/` |
| 31 Versioning and Migration | `migration/v1_server.py`, `migration/v2_server.py` |

## Part IX — Capstone (32)

| Chapter | Code |
|---|---|
| 32 Production AI Operations Server | `capstone/production-ai-operations-mcp/` |

## Tests by chapter

| Chapter | Test file |
|---|---|
| 19 | `projects/productivity-mcp/tests/test_tools.py`, `test_resources.py`, `test_prompts.py`, `test_isolation.py` |
| 20 | `projects/data-engineering-mcp/tests/contract/test_catalogue.py`, `test_output_schema.py`, `tests/test_compatibility.py` |
| 21 | `projects/qa-automation-mcp/tests/failure/test_upstream.py`, `test_no_leaks.py`, `tests/security/test_boundaries.py`, `tests/test_regressions.py` |
| 24 | `projects/data-engineering-mcp/tests/test_auth.py` |
| 32 | `capstone/production-ai-operations-mcp/tests/test_capstone.py` |
