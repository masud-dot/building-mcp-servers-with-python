"""Result models. Every field is a decision to expose it."""

from pydantic import BaseModel, Field


class Service(BaseModel):
    """One service in the catalogue."""

    name: str = Field(description="Service identifier.")
    team: str = Field(description="Team that owns it.")
    tier: int = Field(description="1 is most critical.")


class Health(BaseModel):
    """Current health, from the monitoring system."""

    service: str = Field(description="Service asked about.")
    status: str = Field(description="healthy, degraded or down.")
    error_rate: float = Field(description="Errors per request.")
    p95_ms: int = Field(description="95th percentile latency.")


class Incident(BaseModel):
    """One incident."""

    id: int = Field(description="Identifier for other tools.")
    service: str = Field(description="Affected service.")
    severity: int = Field(description="1 is most severe.")
    summary: str = Field(description="One-line description.")
    status: str = Field(description="open or acknowledged.")
    acknowledged_by: str | None = Field(
        default=None, description="Who acknowledged it."
    )
    opened_at: str = Field(description="ISO 8601 open time.")


class IncidentPage(BaseModel):
    """A page of incidents."""

    incidents: list[Incident] = Field(description="This page.")
    returned: int = Field(description="How many are here.")
    total: int = Field(description="How many matched.")
    truncated: bool = Field(description="More existed.")


class Deployment(BaseModel):
    """One deploy."""

    id: int = Field(description="Deployment identifier.")
    service: str = Field(description="Service deployed.")
    version: str = Field(description="Version deployed.")
    deployed_at: str = Field(description="ISO 8601 time.")


class DiagnosticResult(BaseModel):
    """Output of one named diagnostic."""

    name: str = Field(description="Diagnostic that ran.")
    exit_code: int = Field(description="Process exit code.")
    output: str = Field(description="Combined output, capped.")
    truncated: bool = Field(description="Output was cut.")


class ScanStarted(BaseModel):
    """A handle for work that outlives the call."""

    handle: str = Field(
        description="Pass to get_scan_result. Valid one hour."
    )
    service: str = Field(description="Service being scanned.")


class ScanReport(BaseModel):
    """A scan, running or finished."""

    handle: str = Field(description="The handle asked for.")
    service: str = Field(description="Service scanned.")
    status: str = Field(description="running, complete, failed.")
    matches: int | None = Field(
        default=None, description="Lines matched, when complete."
    )
