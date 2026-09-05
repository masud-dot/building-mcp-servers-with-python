"""Scope enforcement, with authentication switched on.

The rest of the suite runs with auth off, matching the stdio
deployment it tests. These tests turn it on.
"""

import pytest

from mcp.server.mcpserver.exceptions import ToolError

from dataeng import auth
from dataeng.auth.devserver import issue, keypair
from dataeng.auth.verifier import JWTVerifier

pytestmark = pytest.mark.anyio

ISSUER = "http://localhost:9100"
AUDIENCE = "http://localhost:8000/mcp"


@pytest.fixture
def keys():
    return keypair()


@pytest.fixture
def verifier(keys):
    _, public = keys
    return JWTVerifier(public, ISSUER, AUDIENCE)


@pytest.fixture
def enforcing():
    """Turn enforcement on for one test, then off again."""
    auth.configure(True)
    yield
    auth.configure(False)


async def test_valid_token_carries_its_scopes(keys, verifier):
    private, _ = keys
    token = issue(private, "alice", [auth.READ, auth.WRITE])
    access = await verifier.verify_token(token)
    assert access is not None
    assert access.subject == "alice"
    assert set(access.scopes) == {auth.READ, auth.WRITE}


@pytest.mark.parametrize(
    ("label", "overrides"),
    [
        ("wrong audience", {"audience": "http://elsewhere/mcp"}),
        ("wrong issuer", {"issuer": "http://evil"}),
        ("expired", {"lifetime_seconds": -10}),
    ],
)
async def test_bad_tokens_are_rejected(
    keys, verifier, label, overrides
):
    private, _ = keys
    token = issue(private, "eve", [auth.READ], **overrides)
    assert await verifier.verify_token(token) is None


async def test_token_from_another_key_is_rejected(verifier):
    other_private, _ = keypair()
    token = issue(other_private, "eve", [auth.READ])
    assert await verifier.verify_token(token) is None


async def test_malformed_token_is_rejected(verifier):
    assert await verifier.verify_token("not-a-token") is None


def test_no_token_is_refused_when_enforcing(enforcing):
    with pytest.raises(ToolError, match="requires authentication"):
        auth.require(auth.READ)


def test_no_token_passes_when_not_enforcing():
    """Without a verifier there is no identity to check."""
    assert auth.enforcing() is False
    auth.require(auth.WRITE)


def test_enforcement_is_off_by_default():
    """An HTTP deployment refuses to start in this state."""
    assert auth.enforcing() is False
