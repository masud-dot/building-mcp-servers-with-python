"""Running diagnostics without giving anybody a shell.

Chapter 23. Callers choose a name from a fixed registry; they
never supply a command, a path or an argument.
"""

import asyncio
import logging
import sys

from mcp.server.mcpserver.exceptions import ToolError

from aiops.models import DiagnosticResult

logger = logging.getLogger(__name__)

# The complete set this server will ever run. Adding one is a
# code change and a review.
DIAGNOSTICS: dict[str, list[str]] = {
    "python-version": ["-c", "import sys; print(sys.version)"],
    "dns-check": [
        "-c",
        "import socket; print(socket.gethostbyname('localhost'))",
    ],
    "disk-free": [
        "-c",
        "import shutil; print(shutil.disk_usage('/'))",
    ],
}


class DiagnosticRunner:
    """Runs one named diagnostic, bounded."""

    def __init__(
        self, timeout_s: float, max_output: int = 4096
    ) -> None:
        self._timeout = timeout_s
        self._max_output = max_output

    @property
    def names(self) -> list[str]:
        return sorted(DIAGNOSTICS)

    async def run(self, name: str) -> DiagnosticResult:
        if name not in DIAGNOSTICS:
            raise ToolError(
                f"Unknown diagnostic {name!r}. "
                f"Available: {', '.join(self.names)}."
            )
        # An argument vector. No shell, so a metacharacter has
        # nothing to mean.
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            *DIAGNOSTICS[name],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.DEVNULL,
            # Replaced, not inherited: the parent environment
            # holds every credential this server has.
            env={"PATH": "/usr/bin:/bin"},
        )
        try:
            raw, _ = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.warning("diagnostic %s timed out", name)
            raise ToolError(
                f"Diagnostic {name!r} did not finish in "
                f"{self._timeout:.0f} seconds."
            ) from None
        truncated = len(raw) > self._max_output
        return DiagnosticResult(
            name=name,
            exit_code=process.returncode or 0,
            output=raw[: self._max_output].decode(
                "utf-8", errors="replace"
            ),
            truncated=truncated,
        )
