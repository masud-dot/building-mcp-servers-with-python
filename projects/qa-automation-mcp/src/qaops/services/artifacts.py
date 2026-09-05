"""Serving test artefacts from a jailed directory.

Every path a caller supplies goes through safe_join. Nothing
else in the package opens a file.
"""

import mimetypes
import os
from pathlib import Path

from mcp.server.mcpserver.exceptions import ResourceError
from mcp.shared.path_security import PathEscapeError, safe_join

TEXT_TYPES = {".log", ".txt", ".json", ".xml", ".csv", ".md"}


class ArtifactStore:
    """Read-only access to files beneath one root."""

    def __init__(self, root: Path, max_bytes: int) -> None:
        self._root = root.resolve()
        self._max_bytes = max_bytes

    def _resolve(self, name: str) -> Path:
        """The single place a caller's name becomes a path."""
        try:
            return safe_join(self._root, name)
        except PathEscapeError:
            # The reason is deliberately not passed through: it
            # would tell a caller where the root is.
            raise ResourceError(
                f"No artefact named {name!r}."
            ) from None

    def list_names(self) -> list[str]:
        """Names of readable artefacts, symlinks excluded."""
        names = []
        for entry in sorted(self._root.iterdir()):
            if entry.is_symlink() or not entry.is_file():
                continue
            names.append(entry.name)
        return names

    def mime_type(self, name: str) -> str:
        guessed, _ = mimetypes.guess_type(name)
        if guessed:
            return guessed
        suffix = Path(name).suffix.lower()
        return (
            "text/plain" if suffix in TEXT_TYPES
            else "application/octet-stream"
        )

    def read_text(self, name: str) -> tuple[str, bool]:
        """Return file text, capped, and whether it was cut."""
        path = self._resolve(name)
        if not path.is_file():
            raise ResourceError(f"No artefact named {name!r}.")
        size = path.stat().st_size
        # Open without following a final symlink, so a file
        # swapped after the check cannot redirect the read.
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            handle = os.open(path, flags)
        except OSError:
            raise ResourceError(
                f"No artefact named {name!r}."
            ) from None
        try:
            with os.fdopen(handle, "rb") as fh:
                raw = fh.read(self._max_bytes)
        except OSError:
            raise ResourceError(
                f"Artefact {name!r} could not be read."
            ) from None
        text = raw.decode("utf-8", errors="replace")
        return text, size > self._max_bytes
