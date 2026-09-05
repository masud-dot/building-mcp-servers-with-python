"""Result models for the QA automation server."""

from pydantic import BaseModel, Field


class TestRun(BaseModel):
    """One recorded run of a test suite."""

    id: int = Field(description="Run identifier.")
    suite: str = Field(description="Which suite was run.")
    status: str = Field(description="Overall outcome of the run.")
    passed: int = Field(description="Tests that passed.")
    failed: int = Field(description="Tests that failed.")
    started_at: str = Field(description="ISO 8601 start time.")


class Failure(BaseModel):
    """One failing test within a run."""

    test: str = Field(description="Name of the failing test.")
    message: str = Field(description="Assertion or error message.")
    trace_excerpt: str = Field(
        description=(
            "The first part of the stack trace. Truncated; "
            "see trace_truncated."
        )
    )
    trace_truncated: bool = Field(
        description="True when the trace was cut short."
    )


class FailureReport(BaseModel):
    """The failures of one run."""

    run_id: int = Field(description="Run these failures belong to.")
    failures: list[Failure] = Field(
        description="Failing tests, newest first."
    )
    returned: int = Field(description="How many are here.")
    total: int = Field(description="How many the run reported.")
    truncated: bool = Field(
        description="True when more failures existed than returned."
    )
