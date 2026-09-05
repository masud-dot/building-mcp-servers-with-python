# Runbook — Data Engineering MCP server

For whoever is on call. Assumes three instances behind a load
balancer, as in `compose.yaml`.

## What this server is

Read-only access to three warehouse tables, plus one confirmed
delete and a data-quality scan. It holds two database
credentials and verifies bearer tokens issued elsewhere. It
issues no tokens and stores no user data.

## Signals worth alerting on

| Signal | Threshold | Likely cause |
|---|---|---|
| `readyz` failing on one instance | 2 consecutive | Pool exhausted, or database unreachable from that host |
| `readyz` failing on all | 1 | Database down. Page. |
| Error rate on a tool | >5% over 5 min | Upstream change, or a caller with bad arguments |
| p95 on `sample_table` | >2s | Missing index, or a table grew |
| Rate-limit refusals | sustained | One caller looping, or limits set too low |
| Auth rejections | sustained | Key rotated without redeploying |

## First checks

1. `GET /livez` on each instance. A process that fails this is
   restarted by the orchestrator; if it is failing repeatedly,
   read the logs before restarting it again.
2. `GET /readyz`. Distinguishes "process alive" from "database
   reachable". A false `readyz` with a true `livez` is almost
   always the database or the pool.
3. `GET /metrics`. Calls, errors and percentiles per tool.
   Compare tools: one bad tool is a code or data problem, all
   tools is infrastructure.
4. Logs are JSON on stderr. Filter by `trace_id` to follow one
   request; every line from that request carries it.

## Common situations

**One instance failing readiness, others fine.**
Take it out of rotation. Check the pool: `max_size` is 4, so
five concurrent slow queries will exhaust it. Look for a p95
spike on one tool. Restarting clears it and does not fix it.

**All instances failing readiness.**
The database. Nothing in this server will help. Instances will
recover without restarting once it returns.

**Auth rejections after a deploy.**
`DATAENG_AUTH_PUBLIC_KEY` did not change with the issuer's key,
or `DATAENG_AUTH_AUDIENCE` does not match the URL callers use.
The log line names which check failed; the caller is told
nothing.

**Rate limiting a legitimate caller.**
Buckets are per caller identity, 60 tokens refilling at 1/s,
with `sample_table` costing 5 and scans costing 10. A caller
doing bulk work will hit this. Raise the capacity or give them
their own deployment; do not remove the limiter.

**A tool started failing after no deploy.**
Something upstream changed. Check whether the schema moved:
`describe_table` against the affected table. Contract tests
guard the server's own surface, not the database's.

## What not to do

- **Do not disable authentication to unblock a caller.** The
  process refuses to serve HTTP without it, by design.
- **Do not widen the table allow-list to answer a question.**
  It is a code change and a review.
- **Do not grant the read role write access.** The two-role
  split is the control that survives a bug in the code.
- **Do not restart to clear a slow query.** Find it. Restarting
  loses the evidence.

## Rolling a deploy

1. New instance starts, fails `readyz` until its pool opens.
2. Balancer adds it when `readyz` passes.
3. Old instance: readiness withdrawn first, so the balancer
   stops sending work.
4. In-flight requests finish. The lifespan closes the pool.
5. Process exits.

Requests in flight are not dropped provided step 3 precedes
the signal. If it does not, callers see connection resets
during every deploy.

## Escalation

Database problems go to whoever owns the warehouse. Token
rejections go to whoever owns the identity provider. This
server is a resource server and cannot fix either.
