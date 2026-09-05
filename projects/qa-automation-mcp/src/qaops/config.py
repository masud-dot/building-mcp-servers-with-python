"""Settings, read from the environment.

Every value the server needs is declared here, typed, and
validated once at startup. Nothing reads os.environ elsewhere.
"""

import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIX = "QAOPS_"


class Settings(BaseSettings):
    """Configuration for the QA automation server."""

    model_config = SettingsConfigDict(
        env_prefix=PREFIX,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    base_url: str = Field(
        default="http://127.0.0.1:8931",
        description="Root of the test-management API.",
    )
    token: SecretStr = Field(
        default=SecretStr("stub-token"),
        description="Bearer token for that API.",
    )
    connect_timeout: float = Field(default=2.0, gt=0)
    read_timeout: float = Field(default=5.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_trace_chars: int = Field(default=800, ge=100)
    max_failures: int = Field(default=20, ge=1, le=200)
    artifact_root: Path = Field(
        default=Path("./artifacts"),
        description="Directory artefacts are served from.",
    )
    max_artifact_bytes: int = Field(default=64 * 1024, ge=1024)


def warn_unknown_env() -> list[str]:
    """Return prefixed variables that match no setting.

    extra="forbid" catches a misspelling in a .env file but not
    one in a real environment variable, which is the case that
    matters in production. This closes that gap.
    """
    known = {
        f"{PREFIX}{name}".upper()
        for name in Settings.model_fields
    }
    return sorted(
        key
        for key in os.environ
        if key.upper().startswith(PREFIX) and key.upper() not in known
    )
