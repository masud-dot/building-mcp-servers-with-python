# Threat model — Data Engineering MCP server

**Scope:** `projects/data-engineering-mcp`
**Reviewed:** at each release, and whenever a tool is added
**Deployment assumed:** local stdio today; remote HTTP is out
of scope until authentication exists

## 1. What this server can reach

| Asset | Reached via | Sensitivity |
|---|---|---|
| `analytics.customers`, `orders`, `pipeline_runs` | read pool | Business data, personal names |
| `analytics.pipeline_runs` | writer pool | Deletable |
| `analytics.api_credentials` | nothing | Live token, never granted |
| Warehouse credentials | settings | Two DSNs, held as `SecretStr` |

## 2. Who the adversary is

Not a person typing SQL. The realistic adversary is **content**
that reaches the model and influences the arguments it produces.

| Actor | Controls | Motivation |
|---|---|---|
| Author of a customer record | Text in `customers.name` | Reach a tool they cannot call |
| Author of a wiki page or ticket the host also reads | Text in the model's context | Same |
| A compromised or hostile co-connected server | Its own tool descriptions and results | Redirect this server's use |
| The user | Which tools they approve | Usually benign, may be careless |
| An operator | Configuration | Misconfiguration, not malice |

The model itself is not an adversary. It is the **conduit**, and
it is untrusted because its inputs are.

## 3. Trust boundaries

| # | Boundary | Crosses it | Controls |
|---|---|---|---|
| B1 | User → host | Prompts, approvals | Host consent policy. Not ours. |
| B2 | Host → server | Tool arguments, resource URIs | Schema bounds, allow-list, `Literal`, identifier composition |
| B3 | Server → database | SQL | Read-only grant; writer grant limited to one table |
| B4 | Database → server → host | Rows, column names, error text | Row caps, timeouts, withheld exception messages |

B2 is ours and is where every argument arrives untrusted.
B3 is the strongest, because it holds when B2 fails.

## 4. Threats

| ID | Threat | Boundary | Current control | Residual |
|---|---|---|---|---|
| T1 | Arbitrary SQL via a table name | B2 | Allow-list by set membership, then `sql.Identifier` | None known |
| T2 | Reading a table not intended for exposure | B2, B3 | Allow-list, and no `SELECT` grant on it | None known |
| T3 | Any write through the read path | B3 | Read-only role | None known |
| T4 | Deleting rows other than pipeline runs | B3 | Writer grant covers one table | None known |
| T5 | Resource exhaustion by expensive query | B2, B4 | `statement_timeout`, row cap, small pool | A caller may still occupy the pool briefly |
| T6 | Oversized results consuming context and cost | B4 | `LIMIT`, `truncated` flag | Cost is bounded, not zero |
| T7 | Credential disclosure in an error | B4 | `SecretStr`, exception messages withheld | Broken by `ToolError(str(exc))` |
| T8 | Timing disclosure via `elapsed_ms` | B4 | None — accepted | Accepted at current scale |
| T9 | Indirect injection via row content | B4 → B1 | None in this server | **Open.** Host-side problem |
| T10 | Unauthorised deletion | B1, B2 | MRTR typed confirmation | Confirmation is not identity |
| T11 | Any per-caller restriction | — | None: no identity | **Open.** Chapter 24 |
| T12 | Capability composed across servers | outside | None | **Open.** Assistant-side |

## 5. Accepted risks

- **T8, timing.** `elapsed_ms` measures the database. Accepted
  because the data is not confidential at this scale.
- **T9, injection via content.** A customer name is text a
  stranger wrote, and it reaches the model. This server cannot
  fix it; a host can.
- **T11, no identity.** Every caller sees the same three
  tables. Acceptable for a local server the user already has
  database access to. **Not acceptable remotely**, which is why
  remote deployment is out of scope until Chapter 24.

## 6. What would change this model

- Adding a tool that accepts free-text SQL → re-model entirely
- Adding a write beyond `pipeline_runs` → new grant, new row
- Deploying over HTTP → T11 becomes critical, every row revisited
- Adding a table with personal or financial data → revisit T6, T8, T9
