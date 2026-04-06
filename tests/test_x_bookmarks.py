import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from knowledge_compiler.cli import app
from knowledge_compiler.config import Settings
from knowledge_compiler.connectors.x_bookmarks import XApiClient
from knowledge_compiler.services.ingest_x_bookmarks import ingest_x_bookmarks
from knowledge_compiler.storage import WorkspaceStore


def test_x_api_client_requires_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "KNOWLEDGE_COMPILER_X_ACCESS_TOKEN",
        "KNOWLEDGE_COMPILER_X_CONSUMER_KEY",
        "KNOWLEDGE_COMPILER_X_CONSUMER_SECRET",
        "KNOWLEDGE_COMPILER_X_OAUTH_TOKEN",
        "KNOWLEDGE_COMPILER_X_OAUTH_TOKEN_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(OSError, match="KNOWLEDGE_COMPILER_X_ACCESS_TOKEN"):
        XApiClient.from_environment()


def test_x_api_client_oauth1_quartet_only_raises_bookmarks_need_oauth2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_CONSUMER_KEY", "ck")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_CONSUMER_SECRET", "cs")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN", "ot")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN_SECRET", "ots")
    with pytest.raises(OSError, match="OAuth 2.0 User Context"):
        XApiClient.from_environment()


def test_x_api_client_prefers_bearer_when_oauth1_quartet_also_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN", "bearer-wins")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_CONSUMER_KEY", "ck")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_CONSUMER_SECRET", "cs")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN", "ot")
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN_SECRET", "ots")
    client = XApiClient.from_environment()
    assert client._bearer_token == "bearer-wins"


def test_ingest_x_bookmarks_persists_bookmark_posts(tmp_path: Path) -> None:
    settings = Settings.from_project_root(tmp_path)
    store = WorkspaceStore(settings)
    store.ensure_workspace()

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        full_url = getattr(request, "full_url", "")
        if full_url.endswith("/2/users/me") or "/2/users/me?" in full_url:
            payload = {"data": {"id": "user-9", "username": "me"}}
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        if "/2/users/user-9/bookmarks" in full_url:
            payload = {
                "data": [
                    {
                        "id": "tweet-1",
                        "text": "Deterministic chunking keeps citations stable.",
                        "author_id": "42",
                        "created_at": "2024-06-01T12:00:00.000Z",
                    }
                ],
                "includes": {
                    "users": [{"id": "42", "username": "alice", "name": "Alice"}],
                },
                "meta": {"result_count": 1},
            }
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        raise AssertionError(f"unexpected URL {full_url!r}")

    client = XApiClient(bearer_token="test-token", urlopen_fn=fake_urlopen)
    manifest = ingest_x_bookmarks(store=store, client=client, max_pages=1, page_size=10)

    assert manifest.document_count == 1
    assert manifest.chunk_count >= 1

    documents = store.load_documents()
    assert len(documents) == 1
    assert documents[0].relative_path == "x/bookmarks/tweet-1.txt"
    assert documents[0].source_id == "x-bookmarks"
    assert "Deterministic chunking" in store.load_chunks()[0].text
    assert "alice" in store.load_chunks()[0].text.lower()


def test_parse_bookmarks_prefers_note_tweet_text_when_present() -> None:
    payload = {
        "data": [
            {
                "id": "tweet-note",
                "text": "Short card text…",
                "author_id": "99",
                "note_tweet": {"text": "Full long-form note body with more detail than the card."},
            }
        ],
        "includes": {"users": [{"id": "99", "username": "bob", "name": "Bob"}]},
        "meta": {"result_count": 1},
    }
    from knowledge_compiler.connectors import x_bookmarks as xb

    rows = xb._parse_bookmarks_payload(payload)
    assert len(rows) == 1
    assert "Full long-form note body" in rows[0].text
    assert rows[0].text.startswith("Full long-form")


def test_cli_ingest_x_bookmarks_invokes_service(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("knowledge_compiler.cli.ingest_x_bookmarks") as mocked:
        from knowledge_compiler.schemas import IngestManifest

        mocked.return_value = IngestManifest(
            source_id="x-bookmarks",
            document_count=2,
            chunk_count=3,
        )
        result = runner.invoke(
            app,
            ["--project-root", str(tmp_path), "ingest-x-bookmarks", "--max-pages", "1"],
        )
    assert result.exit_code == 0
    assert "2 bookmarked posts" in result.output
    mocked.assert_called_once()
    call_kw = mocked.call_args.kwargs
    assert call_kw["max_pages"] == 1

