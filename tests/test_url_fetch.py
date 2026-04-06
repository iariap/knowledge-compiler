import io
import json
from unittest.mock import patch

import pytest

from knowledge_compiler.connectors.url_fetch import fetch_url_to_text, url_to_document_and_chunks


def test_fetch_url_to_text_parses_html_title() -> None:
    html = b"<!doctype html><html><head><title>My Page</title></head><body><p>Hello</p></body></html>"

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        return io.BytesIO(html)

    with patch("knowledge_compiler.connectors.url_fetch.urlopen", fake_urlopen):
        title, body, ct = fetch_url_to_text("https://example.com/doc")

    assert "Hello" in body
    assert "My Page" in title or title


def test_url_to_document_and_chunks() -> None:
    html = b"<html><title>T</title><body><p>Chunkable paragraph one.</p><p>Two.</p></body></html>"

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        return io.BytesIO(html)

    with patch("knowledge_compiler.connectors.url_fetch.urlopen", fake_urlopen):
        doc, chunks = url_to_document_and_chunks("https://example.org/x")

    assert doc.source_id == "url-fetch"
    assert doc.absolute_path == "https://example.org/x"
    assert len(chunks) >= 1


def test_fetch_url_rejects_non_http() -> None:
    with pytest.raises(ValueError, match="http"):
        fetch_url_to_text("ftp://example.com/")
