"""Fetch a single http(s) URL and normalize to document text."""

from __future__ import annotations

import re
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from knowledge_compiler.ingestion.chunking import chunk_document
from knowledge_compiler.ingestion.html_text import html_to_plain_text
from knowledge_compiler.ingestion.normalize import normalize_text
from knowledge_compiler.schemas import Chunk, Document, Source

_MAX_BYTES = 2_000_000
_TIMEOUT_S = 45
_USER_AGENT = "knowledge-compiler/0.1 (+https://github.com/local-first; local ingest)"

_SOURCE_ID = "url-fetch"


def describe_url_source() -> Source:
    return Source(
        source_id=_SOURCE_ID,
        source_type="url_fetch",
        root_path="https://",
        include_extensions=(),
    )


def fetch_url_to_text(url: str) -> tuple[str, str, str]:
    """Return (title_guess, body_text, content_type_header)."""
    raw_url = url.strip()
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        message = f"URL must be http(s) with a host: {raw_url!r}"
        raise ValueError(message)

    request = Request(
        raw_url,
        headers={"User-Agent": _USER_AGENT},
        method="GET",
    )
    try:
        with urlopen(request, timeout=_TIMEOUT_S) as response:
            headers = getattr(response, "headers", None)
            if headers is not None:
                raw_ct = headers.get("Content-Type") or ""
                content_type = raw_ct.split(";")[0].strip().lower()
            else:
                content_type = ""
            body = response.read(_MAX_BYTES + 1)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        message = f"HTTP {error.code} fetching {raw_url}: {detail}"
        raise OSError(message) from error
    except URLError as error:
        message = f"Failed to fetch {raw_url}: {error}"
        raise OSError(message) from error

    if len(body) > _MAX_BYTES:
        message = f"Response larger than {_MAX_BYTES} bytes; refusing to ingest."
        raise OSError(message)

    text = body.decode("utf-8", errors="replace")
    title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
    if "html" in content_type or text.lstrip().lower().startswith("<!doctype html") or "<html" in text[:500].lower():
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", text, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = normalize_text(html_to_plain_text(title_match.group(1)))[:120] or title
        body_text = normalize_text(html_to_plain_text(text))
    else:
        body_text = normalize_text(text)

    if not body_text:
        message = f"No extractable text from {raw_url}"
        raise OSError(message)

    return title, body_text, content_type


def url_to_document_and_chunks(url: str) -> tuple[Document, list[Chunk]]:
    title, body_text, _ct = fetch_url_to_text(url)
    raw_url = url.strip()
    content_hash = sha256(body_text.encode("utf-8")).hexdigest()
    uhash = sha256(raw_url.encode("utf-8")).hexdigest()[:16]
    relative_path = f"url/{uhash}.txt"
    document = Document(
        document_id=f"doc-{content_hash[:16]}",
        source_id=_SOURCE_ID,
        relative_path=relative_path,
        absolute_path=raw_url,
        title=title or f"URL {uhash}",
        content_hash=content_hash,
    )
    chunks = chunk_document(document, body_text)
    return document, chunks
