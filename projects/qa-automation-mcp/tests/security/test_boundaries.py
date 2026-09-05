"""The controls that leave no trace in the published schema.

Chapter 20 could not defend these: nothing in a tool's schema
says the artefact root is jailed or that traces are trimmed.
Each of these tests names one control and fails if it goes.
"""

import pytest

from mcp import Client
from mcp.server.mcpserver.exceptions import ResourceError
from qaops.services.artifacts import ArtifactStore

pytestmark = pytest.mark.anyio


@pytest.fixture
def jail(tmp_path):
    """A root containing one real file and one escape."""
    (tmp_path / "run.log").write_text("inside the jail")
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("outside the jail")
    (tmp_path / "escape.log").symlink_to(outside)
    return ArtifactStore(tmp_path, max_bytes=1024)


def test_a_real_file_is_served(jail):
    text, truncated = jail.read_text("run.log")
    assert text == "inside the jail"
    assert truncated is False


def test_symlink_escape_is_refused(jail):
    """Only safe_join catches this. Chapter 14."""
    with pytest.raises(ResourceError):
        jail.read_text("escape.log")


def test_traversal_is_refused(jail):
    with pytest.raises(ResourceError):
        jail.read_text("../secret.txt")


def test_absolute_path_is_refused(jail, tmp_path):
    with pytest.raises(ResourceError):
        jail.read_text(str(tmp_path.parent / "secret.txt"))


def test_refusal_does_not_disclose_the_root(jail, tmp_path):
    """The library's message names two absolute paths."""
    with pytest.raises(ResourceError) as raised:
        jail.read_text("escape.log")
    assert str(tmp_path) not in str(raised.value)


def test_the_index_excludes_symlinks(jail):
    assert jail.list_names() == ["run.log"]


def test_reads_are_capped(tmp_path):
    (tmp_path / "big.log").write_text("x" * 5000)
    store = ArtifactStore(tmp_path, max_bytes=1024)
    text, truncated = store.read_text("big.log")
    assert len(text) == 1024
    assert truncated is True
