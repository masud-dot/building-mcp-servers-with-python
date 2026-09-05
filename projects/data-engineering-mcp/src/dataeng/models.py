"""Result models for the data engineering server."""

from pydantic import BaseModel, Field


class Column(BaseModel):
    """One column of a table."""

    name: str = Field(description="Column name.")
    type: str = Field(
        description="SQL type, as the database reports it."
    )
    nullable: bool = Field(description="Whether NULL is permitted.")


class TableSchema(BaseModel):
    """The shape of one table."""

    schema_name: str = Field(description="Schema the table lives in.")
    table: str = Field(description="Table name.")
    columns: list[Column] = Field(description="Columns, in order.")


class QueryResult(BaseModel):
    """Rows returned by a bounded query."""

    columns: list[str] = Field(description="Column names, in order.")
    rows: list[list[str]] = Field(
        description="Rows as text, stringified for display."
    )
    returned: int = Field(description="How many rows are here.")
    truncated: bool = Field(
        description=(
            "True when the row cap stopped more rows being "
            "returned. Narrow the filter or raise limit."
        )
    )
    elapsed_ms: int = Field(description="How long the query took.")


class PipelineRun(BaseModel):
    """One recorded pipeline execution."""

    id: int = Field(description="Run identifier.")
    pipeline: str = Field(description="Pipeline name.")
    status: str = Field(description="Reported status of the run.")
    rows_written: int | None = Field(
        default=None, description="Rows written, null when unknown."
    )
    started_at: str = Field(description="ISO 8601 start time.")


class DeletedRun(BaseModel):
    """What was removed."""

    id: int = Field(description="The run that was deleted.")
    pipeline: str = Field(description="Its pipeline name.")
    deleted: bool = Field(
        description="True when a row was actually removed."
    )
