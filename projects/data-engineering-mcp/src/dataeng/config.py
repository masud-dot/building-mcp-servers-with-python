"""Settings, read from the environment."""

import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIX = "DATAENG_"

DEFAULT_TABLES = (
    "analytics.customers,analytics.orders,"
    "analytics.pipeline_runs"
)


class Settings(BaseSettings):
    """Configuration for the data engineering server."""

    model_config = SettingsConfigDict(
        env_prefix=PREFIX,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    dsn: SecretStr = Field(
        default=SecretStr(
            "postgresql://mcp_reader:localdev"
            "@127.0.0.1/warehouse"
        ),
        description=(
            "Connection string. Contains a password, so it is "
            "held as a secret and never logged."
        ),
    )
    writer_dsn: SecretStr = Field(
        default=SecretStr(
            "postgresql://mcp_writer:localdev"
            "@127.0.0.1/warehouse"
        ),
        description=(
            "Connection string for the one destructive "
            "operation. This role can delete from "
            "pipeline_runs and nothing else."
        ),
    )
    tables: str = Field(
        default=DEFAULT_TABLES,
        description="Comma-separated allow-list of tables.",
    )
    auth_enabled: bool = Field(
        default=False,
        description=(
            "Require a bearer token. Off for stdio, on for "
            "any HTTP deployment."
        ),
    )
    auth_issuer: str = Field(default="http://localhost:9100")
    auth_audience: str = Field(
        default="http://localhost:8000/mcp",
        description="This server's own URL, as the token's aud.",
    )
    auth_public_key: str = Field(
        default="",
        description="PEM public key of the issuer.",
    )
    max_rows: int = Field(default=200, ge=1, le=1000)
    statement_timeout_ms: int = Field(default=5000, ge=100)
    pool_min: int = Field(default=1, ge=0)
    pool_max: int = Field(default=4, ge=1)

    @property
    def table_set(self) -> frozenset[str]:
        """The allow-list, parsed once."""
        return frozenset(
            t.strip() for t in self.tables.split(",") if t.strip()
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
