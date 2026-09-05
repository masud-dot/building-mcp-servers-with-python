"""Verifying bearer tokens as an OAuth resource server.

The server never issues tokens and never sees a password. It
receives a token, checks it was signed by the issuer it trusts,
and checks it was meant for this server.
"""

import logging
import time

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)


class JWTVerifier(TokenVerifier):
    """Checks signature, issuer, audience and expiry."""

    def __init__(
        self,
        public_key: str,
        issuer: str,
        audience: str,
        algorithm: str = "RS256",
    ) -> None:
        self._key = public_key
        self._issuer = issuer
        self._audience = audience
        self._algorithm = algorithm

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return an AccessToken, or None to reject.

        Returning None rather than raising is the protocol the
        SDK expects. Every rejection reason goes to the log; the
        caller learns only that the token was not accepted.
        """
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=[self._algorithm],
                # Both are verified by the library, and both
                # matter. Audience is what stops a token minted
                # for another service being replayed here.
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("rejected token: %s", exc)
            return None

        scopes = claims.get("scope", "").split()
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", claims["sub"]),
            subject=claims["sub"],
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=self._audience,
            claims=claims,
        )


def seconds_remaining(expires_at: int | None) -> int:
    """How long a token has left. Used in logs, not decisions."""
    if expires_at is None:
        return 0
    return max(0, int(expires_at - time.time()))
