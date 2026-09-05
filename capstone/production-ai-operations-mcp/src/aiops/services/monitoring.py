"""The monitoring API. Tools never see HTTP. Chapter 13."""

import logging

import httpx2
from mcp.server.mcpserver.exceptions import ToolError

from aiops.models import Health

logger = logging.getLogger(__name__)
RETRYABLE = {502, 503, 504}


class MonitoringService:
    """A bounded view of somebody else's service."""

    def __init__(
        self, client: httpx2.AsyncClient, max_retries: int = 2
    ) -> None:
        self._client = client
        self._retries = max_retries

    async def health(self, service: str) -> Health:
        attempts = self._retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(
                    f"/health/{service}"
                )
            except httpx2.TimeoutException:
                logger.warning("monitoring timeout (%d)", attempt)
                if attempt == attempts:
                    raise ToolError(
                        "The monitoring service did not respond "
                        "in time. Try again shortly."
                    ) from None
                continue
            except httpx2.RequestError as exc:
                logger.warning("monitoring error: %s", exc)
                if attempt == attempts:
                    raise ToolError(
                        "The monitoring service could not be "
                        "reached."
                    ) from None
                continue
            if response.status_code == 404:
                raise ToolError(f"No such service: {service!r}.")
            if response.status_code in (401, 403):
                logger.error("monitoring rejected our credentials")
                raise ToolError(
                    "This server is not authorised to read "
                    "monitoring. The operator must check its "
                    "credentials."
                )
            if response.status_code >= 400:
                logger.error(
                    "monitoring returned %s", response.status_code
                )
                if (
                    response.status_code in RETRYABLE
                    and attempt < attempts
                ):
                    continue
                raise ToolError(
                    "The monitoring service returned an error."
                )
            return Health(**response.json())
        raise ToolError("The monitoring service is unavailable.")
