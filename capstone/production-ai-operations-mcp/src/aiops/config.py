"""Settings. Chapter 15's pattern, one server later."""

import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIX = "AIOPS_"


class Settings(BaseSettings):
    """Everything an operator decides."""

    model_config = SettingsConfigDict(
        env_prefix=PREFIX,
        env_file=".env",
        extra="forbid",
    )

    dsn: SecretStr = Field(
        default=SecretStr(
            "postgresql://aiops_reader:localdev@127.0.0.1/aiops"
        ),
        description="Read-only connection. Holds a password.",
    )
    writer_dsn: SecretStr = Field(
        default=SecretStr(
            "postgresql://aiops_writer:localdev@127.0.0.1/aiops"
        ),
        description="Acknowledges incidents and stores scans.",
    )
    monitoring_url: str = Field(default="http://127.0.0.1:8955")
    monitoring_token: SecretStr = Field(
        default=SecretStr("stub-token")
    )
    runbook_root: Path = Field(default=Path("./runbooks"))
    max_rows: int = Field(default=100, ge=1, le=500)
    max_runbook_bytes: int = Field(default=32 * 1024, ge=1024)
    statement_timeout_ms: int = Field(default=4000, ge=100)
    diagnostic_timeout_s: float = Field(default=10.0, gt=0)
    auth_enabled: bool = Field(default=False)
    auth_issuer: str = Field(default="http://localhost:9100")
    auth_audience: str = Field(
        default="http://localhost:8000/mcp"
    )
    auth_public_key: str = Field(default="")


def warn_unknown_env() -> list[str]:
    """extra=forbid misses real env vars. Chapter 15."""
    known = {
        f"{PREFIX}{n}".upper() for n in Settings.model_fields
    }
    return sorted(
        k
        for k in os.environ
        if k.upper().startswith(PREFIX) and k.upper() not in known
    )
