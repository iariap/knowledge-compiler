"""Ingest saved posts from X (Twitter) via API v2 bookmarks — no archive export."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from knowledge_compiler.ingestion.chunking import chunk_document
from knowledge_compiler.ingestion.normalize import normalize_text
from knowledge_compiler.schemas import Chunk, Document, Source

_X_API_BASE = "https://api.twitter.com/2"
_DEFAULT_TIMEOUT_S = 60

UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class _TweetPayload:
    tweet_id: str
    text: str
    created_at: str | None
    author_id: str | None
    author_username: str | None
    author_name: str | None


class XApiClient:
    """Minimal X API v2 client using an OAuth 2.0 **user** access token (Bearer).

    X returns HTTP 403 if you call ``GET /2/users/:id/bookmarks`` with OAuth 1.0a
    ("Unsupported Authentication … [OAuth 2.0 User Context]"). Consumer key/secret
    alone are not enough; use PKCE / authorization code to obtain a user token.
    """

    def __init__(
        self,
        *,
        bearer_token: str,
        urlopen_fn: UrlOpen = urlopen,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self._bearer_token = bearer_token.strip()
        self._urlopen_fn = urlopen_fn
        self._timeout_s = timeout_s

    @classmethod
    def from_environment(cls) -> XApiClient:
        token = os.environ.get("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN", "").strip()
        if token:
            return cls(bearer_token=token)
        ck = os.environ.get("KNOWLEDGE_COMPILER_X_CONSUMER_KEY", "").strip()
        cs = os.environ.get("KNOWLEDGE_COMPILER_X_CONSUMER_SECRET", "").strip()
        ot = os.environ.get("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN", "").strip()
        ots = os.environ.get("KNOWLEDGE_COMPILER_X_OAUTH_TOKEN_SECRET", "").strip()
        if ck and cs and ot and ots:
            message = (
                "X API bookmarks require OAuth 2.0 User Context only; OAuth 1.0a is rejected (HTTP 403). "
                "Set KNOWLEDGE_COMPILER_X_ACCESS_TOKEN to a user access token from OAuth 2.0 "
                "(authorization code with PKCE) with scopes tweet.read, users.read, and bookmark.read. "
                "Consumer key/secret are used in the developer app to run that flow, not as a substitute "
                "for the user token on this endpoint."
            )
            raise OSError(message)
        message = (
            "Set KNOWLEDGE_COMPILER_X_ACCESS_TOKEN to an OAuth 2.0 user access token with "
            "tweet.read, users.read, and bookmark.read. The application-only Bearer from the "
            "developer portal cannot call /users/me or bookmarks."
        )
        raise OSError(message)

    def users_me_id(self) -> str:
        payload = self._get_json(f"{_X_API_BASE}/users/me")
        data = payload.get("data") or {}
        user_id = data.get("id")
        if not user_id:
            message = "X API /users/me returned no user id."
            raise ValueError(message)
        return str(user_id)

    def bookmarks_page(
        self,
        user_id: str,
        *,
        max_results: int,
        pagination_token: str | None,
    ) -> tuple[list[_TweetPayload], str | None]:
        params: dict[str, str] = {
            "max_results": str(max(1, min(100, max_results))),
            "expansions": "author_id",
            "tweet.fields": "created_at,author_id,text,note_tweet",
            "user.fields": "username,name",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        query = urlencode(params)
        url = f"{_X_API_BASE}/users/{user_id}/bookmarks?{query}"
        payload = self._get_json(url)
        tweets = _parse_bookmarks_payload(payload)
        next_token = (payload.get("meta") or {}).get("next_token")
        if next_token is not None:
            next_token = str(next_token)
        return tweets, next_token

    def _get_json(self, url: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        request = Request(url, headers=headers)
        try:
            with self._urlopen_fn(request, timeout=self._timeout_s) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            message = f"X API HTTP {error.code} for {url}: {detail}"
            if error.code == 403 and "Application-Only" in detail:
                message += (
                    "\n\nHint: KNOWLEDGE_COMPILER_X_ACCESS_TOKEN must be an OAuth 2.0 *user* access token "
                    "(generate under OAuth 2.0 → your own account), not the App-only Bearer from "
                    '"Autenticación solo de aplicación".'
                )
            if error.code == 402 and "CreditsDepleted" in detail:
                message += (
                    "\n\nHint: X accepted your user token but this endpoint requires API credits on your "
                    "developer account. Check billing/credits in the X developer portal; this is not an "
                    "application bug."
                )
            raise OSError(message) from error
        if not body.strip():
            return {}
        return json.loads(body)


def _parse_bookmarks_payload(payload: dict[str, Any]) -> list[_TweetPayload]:
    users_by_id: dict[str, dict[str, Any]] = {}
    for user in (payload.get("includes") or {}).get("users") or []:
        uid = user.get("id")
        if uid is not None:
            users_by_id[str(uid)] = user

    rows: list[_TweetPayload] = []
    for item in payload.get("data") or []:
        tweet_id = item.get("id")
        text = item.get("text")
        if tweet_id is None:
            continue
        note_obj = item.get("note_tweet")
        if isinstance(note_obj, dict):
            note_text = note_obj.get("text")
            if isinstance(note_text, str) and note_text.strip():
                text = note_text
        if text is None:
            continue
        author_id = item.get("author_id")
        author_id_s = str(author_id) if author_id is not None else None
        user = users_by_id.get(author_id_s) if author_id_s else None
        rows.append(
            _TweetPayload(
                tweet_id=str(tweet_id),
                text=str(text),
                created_at=str(item["created_at"]) if item.get("created_at") else None,
                author_id=author_id_s,
                author_username=str(user["username"]) if user and user.get("username") else None,
                author_name=str(user["name"]) if user and user.get("name") else None,
            )
        )
    return rows


def _format_tweet_document(tweet: _TweetPayload) -> str:
    lines = [tweet.text.strip(), ""]
    meta_parts: list[str] = []
    if tweet.author_username:
        who = f"@{tweet.author_username}"
        if tweet.author_name:
            who = f"{tweet.author_name} ({who})"
        meta_parts.append(who)
    if tweet.created_at:
        meta_parts.append(tweet.created_at)
    if meta_parts:
        lines.append("— " + " · ".join(meta_parts))
    lines.append(f"https://x.com/i/web/status/{tweet.tweet_id}")
    return normalize_text("\n".join(lines))


def _tweet_as_document(*, source_id: str, tweet: _TweetPayload) -> tuple[Document, str]:
    body = _format_tweet_document(tweet)
    content_hash = sha256(body.encode("utf-8")).hexdigest()
    title = _title_from_tweet(tweet)
    relative_path = f"x/bookmarks/{tweet.tweet_id}.txt"
    document = Document(
        document_id=f"doc-{content_hash[:16]}",
        source_id=source_id,
        relative_path=relative_path,
        absolute_path=f"x://bookmark/{tweet.tweet_id}",
        title=title,
        content_hash=content_hash,
    )
    return document, body


def _title_from_tweet(tweet: _TweetPayload) -> str:
    text = " ".join(tweet.text.split())
    if not text:
        return f"Post {tweet.tweet_id}"
    if len(text) <= 80:
        return text
    return text[:77].rstrip() + "…"


class XBookmarksConnector:
    """Fetches the authenticated user's bookmarked posts and turns them into documents."""

    def __init__(
        self,
        client: XApiClient,
        *,
        max_pages: int | None = None,
        page_size: int = 100,
    ) -> None:
        self._client = client
        self._max_pages = max_pages
        self._page_size = page_size

    def describe_source(self) -> Source:
        return Source(
            source_id="x-bookmarks",
            source_type="x_bookmarks",
            root_path=_X_API_BASE,
            include_extensions=(),
        )

    def ingest(self) -> tuple[list[Document], list[Chunk]]:
        source = self.describe_source()
        user_id = self._client.users_me_id()
        tweets = self._collect_bookmarks(user_id)
        documents: list[Document] = []
        chunks: list[Chunk] = []
        for tweet in tweets:
            document, text = _tweet_as_document(source_id=source.source_id, tweet=tweet)
            documents.append(document)
            chunks.extend(chunk_document(document, text))
        return documents, chunks

    def _collect_bookmarks(self, user_id: str) -> list[_TweetPayload]:
        all_tweets: list[_TweetPayload] = []
        token: str | None = None
        pages = 0
        while True:
            page, next_token = self._client.bookmarks_page(
                user_id,
                max_results=self._page_size,
                pagination_token=token,
            )
            all_tweets.extend(page)
            pages += 1
            if self._max_pages is not None and pages >= self._max_pages:
                break
            if not next_token:
                break
            token = next_token
        return all_tweets
