"""A local issuer, for development only.

Real deployments use an identity provider. This exists so the
chapter's examples run without one, and it deliberately has no
login: it mints whatever you ask for.
"""

import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "http://localhost:9100"
AUDIENCE = "http://localhost:8000/mcp"


def keypair() -> tuple[str, str]:
    """A fresh RSA pair. Regenerated on every run."""
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private, public


def issue(
    private_key: str,
    subject: str,
    scopes: list[str],
    lifetime_seconds: int = 900,
    audience: str = AUDIENCE,
    issuer: str = ISSUER,
) -> str:
    """Mint a token. Development only."""
    now = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "client_id": "dev-cli",
            "scope": " ".join(scopes),
            "iat": now,
            "exp": now + lifetime_seconds,
        },
        private_key,
        algorithm="RS256",
    )
