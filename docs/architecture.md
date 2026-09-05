# How the projects are layered

Every server here uses the same layering. It is worth understanding once,
because it is the reason the code is testable and the security controls hold.

```text
        transport            stdio or Streamable HTTP
             │
        middleware           metrics, rate limiting
             │
        authentication       bearer token verification
             │
        tool layer           schemas, scope checks, no I/O
             │
        service layer        database, HTTP, filesystem, subprocess
             │
        credentials          roles, tokens, a jailed root
```

## The tool layer does no I/O

A tool validates, checks a scope, calls a service, and returns a model. It
never builds SQL, never makes an HTTP request, never touches a path.

That separation is not tidiness. It is what makes the failure tests possible:
because a service takes its client in the constructor, a test can hand it a
transport that returns a 503 on demand, and a timeout becomes three lines
rather than an unplugged cable.

## The service layer owns everything dangerous

| Service | Owns | Boundary |
|---|---|---|
| Database | Every query, cap and timeout | Allow-listed tables, composed identifiers |
| HTTP | The upstream client | Fixed base URL, redirects disabled |
| Filesystem | Path resolution | `safe_join` against a fixed root |
| Subprocess | Execution | Fixed registry, argument vector, no shell |

A caller supplies a **name**, never a path, a command or a URL. That is the
single most important design rule in the repository: the attacks are not
detected, they are inexpressible.

## State lives in the lifespan

Connection pools, HTTP clients and background task groups are opened once at
startup and closed in reverse on shutdown. Nothing is module-level.

Two consequences: each connection gets fresh state, which is what makes tests
independent of each other; and anything a caller expects to come back for
cannot live there, because it would be per instance. Long-running work returns
an unguessable handle and stores its result in the database, so any instance
can answer.

## The grants are the real boundary

Both database projects use two roles with different privileges. The read role
cannot write. The write role can change exactly one table and cannot read the
credentials table that sits in the schema specifically to prove it.

If every check in the Python were wrong, the grant would still bound the
damage. That is why the schema is written and verified before the server code
— the security boundary is an architectural input, not something added
afterwards.

## Errors are asymmetric

A refusal tells the caller what they can do and nothing about why the check
fired. The detail goes to the log:

```python
logger.warning("refused %s: %s", target, reason)
raise ToolError("That endpoint is not one this server may contact.")
```

"Resolves inward" in a caller-visible message would confirm to an attacker
that their DNS rebinding worked.

## Observability

Structured JSON logs on stderr carrying `trace_id`, so a log line and a trace
are the same investigation. The SDK emits its own `SERVER` spans and
propagates trace context from the caller, so the projects add **metrics**
middleware rather than tracing middleware.

One detail worth knowing: middleware sits above model validation, so it
receives wire-form dictionaries. The error count reads `isError`, camelCase,
not `is_error`.
