"""Lexical clustering of compiled topics into coarse themes (no embeddings)."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from re import sub

from knowledge_compiler.retrieval.query_tokens import STOPWORDS, lexical_token_set
from knowledge_compiler.schemas import TopicRecord
from knowledge_compiler.schemas.manifests import TopicThemeEntry


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, x: int) -> int:
        parent = self._parent
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def _keyword_set(topic: TopicRecord) -> frozenset[str]:
    blob = f"{topic.title} {topic.summary}"
    return frozenset(
        w for w in lexical_token_set(blob) if len(w) > 2 and w not in STOPWORDS
    )


def _similarity_link(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    inter = len(a & b)
    if inter < 2:
        return False
    union = len(a | b)
    return union > 0 and (inter / union) >= 0.12


def cluster_topics_lexical(
    topics: list[TopicRecord],
) -> tuple[tuple[TopicThemeEntry, ...], dict[str, tuple[str, str]]]:
    """Group topics by overlapping keywords; label each group from frequent terms."""
    n = len(topics)
    if n == 0:
        return (), {}

    key_sets = [_keyword_set(t) for t in topics]
    uf = _UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if _similarity_link(key_sets[i], key_sets[j]):
                uf.union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = uf.find(i)
        clusters.setdefault(root, []).append(i)

    topic_to_theme: dict[str, tuple[str, str]] = {}
    entries: list[TopicThemeEntry] = []

    for members in clusters.values():
        members.sort(key=lambda idx: topics[idx].topic_id)
        blob = " ".join(f"{topics[i].title} {topics[i].summary}" for i in members)
        words = [w for w in lexical_token_set(blob) if len(w) > 2 and w not in STOPWORDS]
        frequent = [word for word, _ in Counter(words).most_common(4)]
        label = " · ".join(frequent) if frequent else "misc"
        if len(label) > 120:
            label = label[:117] + "…"
        digest = sha256("".join(topics[i].topic_id for i in members).encode()).hexdigest()[:8]
        slug_base = sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48] or "theme"
        theme_id = f"{slug_base}-{digest}"
        tids = tuple(topics[i].topic_id for i in members)
        entries.append(TopicThemeEntry(theme_id=theme_id, label=label, topic_ids=tids))
        for i in members:
            topic_to_theme[topics[i].topic_id] = (theme_id, label)

    entries.sort(key=lambda e: (-len(e.topic_ids), e.theme_id))
    return tuple(entries), topic_to_theme
