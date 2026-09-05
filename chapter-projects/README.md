# Chapter projects

Standalone examples that belong to a single chapter. Each is independent and
none is needed by the four main projects.

| Directory | Chapter | What it shows |
|---|---|---|
| `05-setup/` | 5 | A correctly pinned project skeleton, and the `.env` pattern |
| `06-first-server/` | 6 | The whole server in about thirty lines, plus its four silent failure modes |
| `16-client/` | 16 | A command-line MCP client: list, call, read |
| `17-multi-server/` | 17 | One assistant connected to three servers at once |
| `29-extensions/` | 29 | A custom extension using all four contribution points, and an MCP Apps UI that degrades to text |
| `30-long-running/` | 30 | Progress, handles and a Tasks extension built by hand, compared |

Each directory with a `pyproject.toml` installs with `uv sync`. The smaller
examples are single files that run against any environment where
`mcp==2.1.1` is installed.
