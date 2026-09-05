"""The only code that knows the upstream API exists.

Tools call these methods. They never see a URL, a token, a
status code or an httpx2 exception.
"""

import asyncio
import logging

import httpx2

from qaops.config import Settings
from qaops.models import Failure, FailureReport, TestRun
from mcp.server.mcpserver.exceptions import ToolError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {502, 503, 504}


class UpstreamUnavailable(ToolError):
    """The upstream could not answer, and retrying may help."""


class TestRunService:
    """A bounded view of the test-management API."""

    def __init__(
        self, client: httpx2.AsyncClient, settings: Settings
    ) -> None:
        self._client = client
        self._settings = settings

    async def _get(self, path: str) -> dict:
        """One GET, with bounded retries and mapped failures."""
        attempts = self._settings.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(path)
            except httpx2.TimeoutException:
                logger.warning(
                    "upstream timeout on %s (attempt %d)",
                    path,
                    attempt,
                )
                if attempt == attempts:
                    raise UpstreamUnavailable(
                        "The test service did not respond in time. "
                        "Try again shortly."
                    ) from None
            except httpx2.RequestError as exc:
                logger.warning("upstream error on %s: %s", path, exc)
                if attempt == attempts:
                    raise UpstreamUnavailable(
                        "The test service could not be reached."
                    ) from None
            else:
                mapped = self._map_status(response)
                if mapped is None:
                    return response.json()
                if response.status_code not in RETRYABLE_STATUS:
                    raise mapped
                if attempt == attempts:
                    raise mapped
            await asyncio.sleep(0.2 * attempt)
        raise UpstreamUnavailable("The test service is unavailable.")

    def _map_status(self, response) -> ToolError | None:
        """Turn an upstream status into something a model can use."""
        code = response.status_code
        if code < 400:
            return None
        if code == 401 or code == 403:
            logger.error("upstream rejected our credentials")
            return ToolError(
                "This server is not authorised to read test "
                "results. The operator needs to check its "
                "credentials."
            )
        if code == 404:
            return ToolError("No such test run.")
        if code == 429:
            after = response.headers.get("Retry-After", "a while")
            return ToolError(
                f"The test service is rate limiting requests. "
                f"Wait {after} seconds and try again."
            )
        logger.error(
            "upstream returned %s for %s", code, response.url
        )
        return UpstreamUnavailable(
            "The test service returned an error."
        )

    async def list_runs(self) -> list[TestRun]:
        payload = await self._get("/runs")
        return [TestRun(**run) for run in payload["runs"]]

    async def get_run(self, run_id: int) -> TestRun:
        return TestRun(**await self._get(f"/runs/{run_id}"))

    async def failures(self, run_id: int) -> FailureReport:
        """Failures for one run, with traces trimmed."""
        payload = await self._get(f"/runs/{run_id}/failures")
        raw = payload["failures"]
        cap = self._settings.max_failures
        limit = self._settings.max_trace_chars
        trimmed = []
        for item in raw[:cap]:
            trace = item.get("trace", "")
            trimmed.append(
                Failure(
                    test=item["test"],
                    message=item["message"],
                    trace_excerpt=trace[:limit],
                    trace_truncated=len(trace) > limit,
                )
            )
        return FailureReport(
            run_id=run_id,
            failures=trimmed,
            returned=len(trimmed),
            total=len(raw),
            truncated=len(raw) > cap,
        )
