# Plan: pending work

This file is a **living backlog** of what is still worth building, given the
current codebase. It complements **`TRD.md`** (what the system is required to
do today) and **`README.md`** (why it exists and how it is shaped). When you pick
a slice, update this file so the gap between “intended” and “implemented” stays
honest.

---

## Baseline (already shipped)

The CLI already covers local and **HTML** ingest, **`ingest-url`**, **X
bookmarks** (including **`note_tweet`** when present), **`--merge`** for
multi-source workspaces with **unchanged-file reuse** on merge, compile
(**themes**, **lexical cross-topic** relations), **SQLite FTS**, diversified
retrieval, optional **`--embed-rerank`** (OpenAI-compatible embeddings, in
memory only), **tiktoken** caps on context, heuristic **`ask`**, optional **`ask
--llm`**, **`inspect`**, **`trace`** / **`trace --run`**, and **`runs`**.

That baseline is assumed below; the pending items are **extensions or hardening**,
not a restatement of the MVP.

---

## Near term (high leverage, still local-first)

**Compile and graph.** Today there is **one topic per ingested document** and
claims are thin. Pending: optional **multi-topic splits** inside a single
document (for example Markdown heading boundaries), **richer claims** (multiple
chunks, simple certainty or scope fields if they stay inspectable), and **relation
types** that reflect the corpus (not only `contains_claim` and
`lexically_related_to`). Any new edge should remain **serializable and traceable**
in JSON/JSONL.

**Retrieval and evidence.** Optional **`--embed-rerank`** helps ordering but
**recall** is still FTS-bounded. Pending: optional **query expansion** or
**synonym/alias** layers that log what was expanded; **cached embedding index**
on disk (still not a separate “vector DB product”—think one SQLite table or file
per workspace) if we want offline rerank without round-trips per query; clearer
**EvidencePack** provenance (why this hit ranked here).

**Ingestion.** URL fetch is deliberately minimal. Pending: **robots / size /
redirect** policy switches, optional **single-page readability** extraction for
noisy HTML, and **incremental ingest** keyed by source metadata (for example
“only fetch if etag changed”) without breaking merge semantics.

**Trust and ops.** Pending: **schema migration notes** when artifact shapes
change; stricter **validation** on load for mixed-version workspaces; optional
**export** of a query bundle (evidence + context + answer) as one archive for
reviews.

---

## Medium term (still consistent with traceability)

**Answer and models.** Tighter **prompt contracts** and optional **structured
output** (JSON) for `ask --llm` so failures are machine-detectable; **pluggable
chat endpoints** behind a small protocol (same env-key story, no framework).

**Inspection.** Beyond **`trace --run`**: browse **arbitrary** `query-runs.jsonl`
entries with stable ids, or a thin **TUI** that lists runs and opens artifacts.

**Connectors.** Additional **single-purpose** connectors (mail export, RSS,
git-aware notes) that feed the **same** normalize → chunk path—still no generic
plugin marketplace until a second connector proves the interface.

---

## Explicitly deferred (see README “What we are not doing yet”)

Not scheduled in this plan unless requirements change: **hosted multi-tenant
services**, **graph query engines** as a product surface, **vector-database
vendors** as a hard dependency, **background job runners**, **SaaS auth/billing**,
and **broad plugin registries**. Those are intentional boundaries so the local
knowledge engine stays small and auditable.

---

## How to use this plan

Pick **one vertical slice** (for example “heading-based topic split” or “cached
chunk embeddings file”), implement it with **tests for behavior that matters**,
update **`TRD.md`** / **`README.md`** / **`practical-guide.md`** when behavior or
operators’ workflows change, then trim or reorder this file so it stays a backlog,
not a second specification.
