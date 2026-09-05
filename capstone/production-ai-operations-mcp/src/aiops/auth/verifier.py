"""An OAuth resource server. It verifies; it never issues."""

import logging

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

logger = logging.getLogger(__name__)


class JWTVerifier(TokenVerifier):
    """Signature, issuer, audience, expiry, and required claims."""

    def __init__(
        self, public_key: str, issuer: str, audience: str
    ) -> None:
        self._key = public_key
        self._issuer = issuer
        self._audience = audience

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            # The reason is logged; the caller learns nothing.
            logger.warning("rejected token: %s", exc)
            return None
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", claims["sub"]),
            subject=claims["sub"],
            scopes=claims.get("scope", "").split(),
            expires_at=int(claims["exp"]),
            resource=self._audience,
            claims=claims,
        )
