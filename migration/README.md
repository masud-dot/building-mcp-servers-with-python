# Migration — v1 to v2

The same server twice: once as it was written for the SDK's 1.x line, once
after the six changes needed for 2.x.

| File | Runs on |
|---|---|
| `v1_server.py` | `mcp>=1.28,<2` |
| `v2_server.py` | `mcp==2.1.1` |

Run `v1_server.py` against 2.x and the SDK tells you exactly what happened:

```text
ModuleNotFoundError: No module named 'mcp.server.fastmcp'.
This is mcp 2.x, where FastMCP was renamed to MCPServer ...
```

The decorators do not change. `@server.tool()`, `@server.resource(uri)` and
`@server.prompt()` are identical across the two majors — the migration is the
import, the class name, the run call, and three renamed result attributes.

Chapter 31 walks through it, including the renames that fail silently rather
than loudly.
