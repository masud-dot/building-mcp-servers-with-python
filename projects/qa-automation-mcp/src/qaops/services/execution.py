"""Running tests, without giving anybody a shell.

Callers choose a suite by name from a fixed registry. They
never supply a command, a path, or an argument.
"""

import asyncio
import logging

from mcp.server.mcpserver.exceptions import ToolError

logger = logging.getLogger(__name__)

# The complete set of things this server will ever run. Adding
# an entry is a code change and a review, which is the point.
SUITES: dict[str, list[str]] = {
    "smoke": ["-m", "pytest", "-q", "-k", "smoke"],
    "checkout": ["-m", "pytest", "-q", "tests/checkout"],
    "search": ["-m", "pytest", "-q", "tests/search"],
}


class SuiteRunner:
    """Runs one of a fixed set of suites, bounded."""

    def __init__(
        self,
        interpreter: str,
        working_dir: str,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> None:
        self._interpreter = interpreter
        self._working_dir = working_dir
        self._timeout = timeout_seconds
        self._max_output = max_output_bytes

    @property
    def names(self) -> list[str]:
        return sorted(SUITES)

    async def run(self, suite: str) -> tuple[str, int, bool]:
        """Run one named suite. Returns output, code, truncated."""
        if suite not in SUITES:
            raise ToolError(
                f"Unknown suite {suite!r}. "
                f"Available: {', '.join(self.names)}."
            )
        # An argument vector, not a string. There is no shell,
        # so there is nothing for a metacharacter to mean.
        argv = [self._interpreter, *SUITES[suite]]
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=self._working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "HOME": self._working_dir},
        )
        try:
            raw, _ = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.warning("suite %s exceeded its timeout", suite)
            raise ToolError(
                f"Suite {suite!r} did not finish within "
                f"{self._timeout:.0f} seconds."
            ) from None
        truncated = len(raw) > self._max_output
        text = raw[: self._max_output].decode(
            "utf-8", errors="replace"
        )
        return text, process.returncode or 0, truncated
