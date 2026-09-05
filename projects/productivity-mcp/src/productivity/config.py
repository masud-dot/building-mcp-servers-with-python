"""Settings, read from the environment.

This server has no secrets. It uses the same pattern anyway,
so that every project in the book is configured one way.
"""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIX = "PRODUCTIVITY_"


class Settings(BaseSettings):
    """Configuration for the productivity server."""

    model_config = SettingsConfigDict(
        env_prefix=PREFIX,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    recent_notes: int = Field(
        default=5,
        ge=1,
        le=50,
        description="How many notes notes://recent returns.",
    )
    max_page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Largest page list_tasks will return.",
    )


def warn_unknown_env() -> list[str]:
    """Prefixed variables that match no setting."""
    known = {
        f"{PREFIX}{name}".upper() for name in Settings.model_fields
    }
    return sorted(
        key
        for key in os.environ
        if key.upper().startswith(PREFIX)
        and key.upper() not in known
    )
