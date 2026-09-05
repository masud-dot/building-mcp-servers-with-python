"""Fetching a caller-named endpoint, safely.

Chapter 13 avoided this problem by fixing the host in
configuration. This is for the case where a caller genuinely
must choose, and it is deliberately restrictive.
"""

import ipaddress
import logging
import socket

import httpx2
from mcp.server.mcpserver.exceptions import ToolError

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_HOPS = 3


class EndpointChecker:
    """Fetches only from an allow-listed set of origins."""

    def __init__(
        self,
        allowed_origins: frozenset[str],
        max_bytes: int,
        timeout_seconds: float,
        allow_private: bool = False,
    ) -> None:
        self._allowed = allowed_origins
        self._max_bytes = max_bytes
        self._timeout = timeout_seconds
        self._allow_private = allow_private

    def _refuse(self, reason: str, url: str) -> ToolError:
        """Log the detail, tell the caller almost nothing."""
        logger.warning("refused %s: %s", url, reason)
        return ToolError(
            "That endpoint is not one this server may contact. "
            f"Allowed: {', '.join(sorted(self._allowed))}."
        )

    def _check(self, url: httpx2.URL) -> None:
        """Every rule, applied to one URL. Raises on refusal."""
        if url.scheme not in ALLOWED_SCHEMES:
            raise self._refuse("scheme", str(url))

        origin = f"{url.scheme}://{url.netloc.decode()}"
        if origin not in self._allowed:
            raise self._refuse("origin not allow-listed", str(url))

        if self._allow_private:
            return

        # Resolve, then judge the address rather than the name.
        # A name that resolves inward is the rebinding case.
        try:
            resolved = socket.getaddrinfo(
                url.host, url.port or 0, proto=socket.IPPROTO_TCP
            )
        except socket.gaierror:
            raise self._refuse("does not resolve", str(url)) from None
        for entry in resolved:
            address = ipaddress.ip_address(entry[4][0])
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
            ):
                raise self._refuse("resolves inward", str(url))

    async def check(self, url: str) -> tuple[int, str, bool]:
        """Fetch one endpoint. Returns status, body, truncated."""
        target = httpx2.URL(url)
        async with httpx2.AsyncClient(
            follow_redirects=False, timeout=self._timeout
        ) as client:
            for _ in range(MAX_HOPS):
                # Every hop is checked, not just the first.
                self._check(target)
                response = await client.get(target)
                redirects = (301, 302, 303, 307, 308)
                if response.status_code not in redirects:
                    body = response.text[: self._max_bytes]
                    return (
                        response.status_code,
                        body,
                        len(response.text) > self._max_bytes,
                    )
                location = response.headers.get("location", "")
                target = target.join(location)
        raise self._refuse("too many redirects", url)
