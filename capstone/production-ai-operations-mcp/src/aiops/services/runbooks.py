"""Runbooks from a jailed directory. Chapter 14."""

import os
from pathlib import Path

from mcp.server.mcpserver.exceptions import ResourceError
from mcp.shared.path_security import PathEscapeError, safe_join


class RunbookStore:
    """Read-only access to files beneath one root."""

    def __init__(self, root: Path, max_bytes: int) -> None:
        self._root = root.resolve()
        self._max_bytes = max_bytes

    def names(self) -> list[str]:
        if not self._root.is_dir():
            return []
        return sorted(
            e.name
            for e in self._root.iterdir()
            if e.is_file() and not e.is_symlink()
        )

    def read(self, name: str) -> tuple[str, bool]:
        """The single place a caller's name becomes a path."""
        try:
            path = safe_join(self._root, name)
        except PathEscapeError:
            # The library's message names two absolute paths.
            raise ResourceError(
                f"No runbook named {name!r}."
            ) from None
        if not path.is_file():
            raise ResourceError(f"No runbook named {name!r}.")
        size = path.stat().st_size
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except OSError:
            raise ResourceError(
                f"No runbook named {name!r}."
            ) from None
        with os.fdopen(fd, "rb") as fh:
            raw = fh.read(self._max_bytes)
        return (
            raw.decode("utf-8", errors="replace"),
            size > self._max_bytes,
        )
