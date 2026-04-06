# Practical Guide: Using the Knowledge Compiler

This booklet is the **hands-on manual** for `knowledge-compiler`: how to run it,
what each command does, how artifacts fit together as a small **local knowledge
graph** (topics, claims, relations), and how to stay grounded when you query.

`README.md` stays the project essay—motivation, architecture, principles. **This
file is for day-to-day use.**

---

## Contents

1. [What you are building](#1-what-you-are-building) — includes [what “KG” means](#what-is-a-knowledge-graph-kg)
2. [Install and first run](#2-install-and-first-run) — includes [example teaching workflow](#example-workflow-for-teaching)
3. [Project root and `workspace/`](#3-project-root-and-workspace)
4. [End-to-end pipeline](#4-end-to-end-pipeline)
5. [Ingest: files, HTML, merge, X bookmarks](#5-ingest-files-html-merge-x-bookmarks)
6. [Compile and index](#6-compile-and-index) — includes [what SQLite FTS is](#what-is-sqlite-fts-and-fts5)
7. [The compiled graph](#7-the-compiled-graph)
8. [Querying: retrieve and context](#8-querying-retrieve-and-context)
9. [Ask: heuristic vs LLM](#9-ask-heuristic-vs-llm)
10. [Inspect, trace, and runs](#10-inspect-trace-and-runs)
11. [Good habits and debugging order](#11-good-habits-and-debugging-order)
12. [Troubleshooting](#12-troubleshooting)
13. [Limitations](#13-limitations)
14. [X bookmarks: auth notes (ES)](#14-x-bookmarks-auth-notes-es)

---

## 1. What you are building

### What is a knowledge graph (KG)?

A **knowledge graph** is a way of representing information as **things** (often
called entities or nodes) connected by **typed relationships** (edges). Unlike a
single long document, a KG makes structure explicit: you can say “this topic
*contains* this claim,” “this topic is *lexically related to* that topic,” or
“this answer is *supported by* this evidence chunk,” and you can follow those
links when you inspect or debug the system.

In research and industry, “KG” sometimes implies huge graphs, semantic web
standards, or machine learning pipelines. Here it means the same **idea**
—nodes and relations you can traverse—at a **small, local** scale: your compiled
artifacts are the graph, and the CLI is how you build it and query it honestly.

### In this tool, that means…

The tool turns sources into **stable chunks** with provenance, compiles a first
layer of **topics and claims**, links **relations** (within topics and across
topics when vocabulary overlaps), indexes text with **SQLite FTS**, and answers
questions with **citations** to real chunks—not vibes.

Think of it as a **local, inspectable knowledge graph** backed by files: every
interesting step writes JSON/JSONL/Markdown/SQLite you can open and diff.

---

## 2. Install and first run

```bash
uv sync
```

Run the fixture corpus through the full chain:

```bash
uv run knowledge-compiler ingest tests/fixtures/input
uv run knowledge-compiler compile
uv run knowledge-compiler index
uv run knowledge-compiler retrieve "deterministic chunking"
uv run knowledge-compiler context "deterministic chunking"
uv run knowledge-compiler ask "deterministic chunking"
uv run knowledge-compiler trace
uv run knowledge-compiler runs
```

That sequence teaches the pipeline: **evidence → context → answer → proof**.

### Example workflow for teaching

Use this when you are walking someone through the tool for the first time; it
stays entirely on the **fixture corpus** shipped with the repo so everyone sees
the same files and the same plausible answers.

Have learners run the commands in order and pause after each block to open the
artifact that changed. The goal is not memorizing flags—it is seeing **how each
stage constrains the next**, which is what “grounded KG” practice looks like.

**1. Environment.** From the repository root, run `uv sync`, then show that the
CLI resolves with `uv run knowledge-compiler --help`.

**2. Build the graph (batch).** Run `ingest`, `compile`, and `index` on
`tests/fixtures/input` as in the block above. Open `workspace/state/chunks.jsonl`
and point out one line: that is a **node** of evidence with a stable id and
provenance. Open `workspace/compiled/topics.json` and explain that each row is a
**topic node** tied to chunks. Skim one file under `workspace/compiled/topics/`
to connect the human-readable page to those ids.

**3. Show retrieval as a separate decision.** Run `retrieve "deterministic chunking"`.
Emphasize that nothing has been “answered” yet—this step only says which chunks
scored highly and what topics/claims overlap. If you delete or break
`workspace/indexes/retrieval.db` and repeat, the command fails until `index` is
run again; that reinforces that the KG’s **searchable layer** is explicit and
rebuildable.

**4. Show context as a budget, not the whole corpus.** Run
`context "deterministic chunking" --max-chars 400` and compare the output to
`retrieve` for the same query. The graph is the same; the **pack** is the slice
you allow downstream code (or a model) to see.

**5. Answer and then audit.** Run `ask "deterministic chunking"`, then immediately
`trace`. The teaching point is simple: the answer text is cheap to doubt; the
**cited chunk bodies** in `trace` are the accountability bridge back to source
lines. Optionally run `runs` and `trace --run <id>` so the room sees that history
can be replayed, not only the latest `last-answer.json`.

**6. Optional stretch.** If the audience is comfortable, repeat `retrieve` with
`--match or` or `--embed-rerank` (with an API key) and compare hit ordering—same
KG, different **retrieval policy**—or mention `ingest-url` / `--merge` as ways to
grow the corpus without throwing away prior sources.

---

## 3. Project root and `workspace/`

Commands run against a **project root**: the directory that contains
`workspace/`. Resolution order:

1. **`knowledge-compiler -p /path/to/root …`**
2. **`KNOWLEDGE_COMPILER_ROOT`**
3. **Current working directory**

All paths below are relative to that root.

| Location | Role |
| -------- | ---- |
| `workspace/state/` | Ingest output, query caches, run history |
| `workspace/compiled/` | Topics, claims, relations, manifests |
| `workspace/indexes/` | `retrieval.db` (FTS) |

Optional: copy `.env.example` to `.env` in the project root for API keys (X,
OpenAI-compatible LLM). The CLI loads dotenv early.

---

## 4. End-to-end pipeline

**Offline (batch):** `ingest` → `compile` → `index` whenever sources or policy
change.

**Online (query):** `retrieve` (optional debug) → `context` (optional debug) →
`ask` → `trace` / `runs` when you need accountability.

Re-run **`index`** after any ingest or compile that changes chunks. Stale indexes
produce empty or wrong answers.

---

## 5. Ingest: files, HTML, URLs, merge, X bookmarks

### Local folders

```bash
uv run knowledge-compiler ingest /path/to/my-notes
```

Recursively ingests **`md`**, **`txt`**, **`html`**, **`htm`**. HTML is reduced to
visible text (script/style stripped); it is not a full “reader mode” cleaner.

### URLs (http/https)

```bash
uv run knowledge-compiler ingest-url https://example.com/page --merge
```

Fetches each URL (size-capped), strips HTML like local `.html`, and stores under
source id **`url-fetch`**. Use **`--merge`** to keep folder or bookmark sources.
Then **`compile`** and **`index`**.

### Merge (multi-source workspace)

Default ingest **replaces** the whole `workspace/state/` bundle. To **add** or
refresh one connector without deleting others:

```bash
uv run knowledge-compiler ingest /path/to/more-notes --merge
```

The same **`--merge`** flag exists on **`ingest-x-bookmarks`** and **`ingest-url`**. Each source has a
stable `source_id`; merge drops prior rows for *that* id, keeps other sources,
and skips new documents whose `document_id` already exists (avoids duplicate
chunk ids). When you **`--merge`** the **same** folder (or URL source) again,
unchanged files (same `relative_path` and `content_hash`) **reuse** existing
chunks instead of rewriting them.

After merging sources, run **`compile`** and **`index`** on the **combined**
corpus.

### X bookmarks

```bash
uv run knowledge-compiler ingest-x-bookmarks
```

Requires **`KNOWLEDGE_COMPILER_X_ACCESS_TOKEN`** (OAuth 2.0 user token with
`tweet.read`, `users.read`, `bookmark.read`). See [§14](#14-x-bookmarks-auth-notes-es)
for Spanish notes on why OAuth 1.0a fails.

The client requests **`note_tweet`** in `tweet.fields`. When present, the long
note body is stored; otherwise the regular `text` field is used.

Optional: **`--max-pages`**, **`--page-size`**, **`--merge`**.

---

## 6. Compile and index

```bash
uv run knowledge-compiler compile
uv run knowledge-compiler index
```

**Compile** groups chunks by document, emits one **topic** per document (Markdown
under `workspace/compiled/topics/`), simple **claims**, **relations**
(`contains_claim` inside each topic), **lexical themes** (keyword clusters on
title+summary), and **cross-topic** edges (`lexically_related_to`) when two
topics overlap enough. Counts and metadata live in **`compile-manifest.json`**.

**Index** rebuilds **`workspace/indexes/retrieval.db`** (FTS5). Treat it as
disposable.

### What is SQLite FTS (and FTS5)?

**FTS** means **Full-Text Search** inside **SQLite**: the database keeps an
**inverted index** of words (tokens) found in your chunk text, so queries can
find matching rows quickly using **`MATCH`**-style search instead of scanning
every chunk with a naive substring filter.

**FTS5** is the current SQLite full-text module. This project stores indexed
chunk text there so **`retrieve`**, **`context`**, and **`ask`** share one
**local** search layer: no separate search server, and you can delete
**`retrieval.db`** and rebuild it anytime with **`index`**.

FTS search is **lexical**: it cares about **which terms appear** (and how you
combine them—see **`--match and`** vs **`--or`**), not about “meaning” in the
embedding sense. Ranking uses the engine’s relevance scoring (BM25-style in
practice for FTS5), then this tool may **rerank** or **diversify** hits (lexical
overlap, per-document caps, optional **embedding** reordering) on top of that
list.

So when the booklet says “FTS” or “lexical retrieval,” read it as: **word-level
search in SQLite**, fast and inspectable, with citations still pointing to real
chunks—not as a semantic or neural retrieval stack unless you opt into
**`--embed-rerank`**.

---

## 7. The compiled graph

| Artifact | Meaning |
| -------- | ------- |
| `topics.json` / `topics/*.md` | One topic per ingested document; summary + evidence |
| `claims.jsonl` | Short claim strings tied to chunks |
| `relations.jsonl` | `contains_claim` per topic; **`xref-*`** cross-topic links |
| `compile-manifest.json` | `themes`, `lexical_cross_topic_links`, counts |

**Themes** and **cross-topic links** are both **lexical** (Jaccard-style overlap),
not neural embeddings. They are explainable and cheap, not “true” semantic
clustering.

---

## 8. Querying: retrieve and context

```bash
uv run knowledge-compiler retrieve "your query"
uv run knowledge-compiler context "your query" --max-chars 1500
```

**Retrieve** shows the **`EvidencePack`**: hits, scores, line ranges.

**Context** builds the **`ContextPack`**: the snippets that fit the character
budget (often **multiple** snippets), plus an **estimated token** hint. You can
add **`--max-tokens N`** so snippet assembly stops when **tiktoken** (`cl100k_base`)
counts reach that ceiling (character budget still applies in parallel).

Shared tuning flags (also on **`ask`**):

| Flag | Effect |
| ---- | ------ |
| `--match and` (default) | All query terms must match in FTS |
| `--match or` | Any term may match |
| `--candidate-pool N` | More raw hits before diversify/rerank |
| `--max-per-document K` | Cap chunks per document in ranked list |
| `--embed-rerank` | After FTS, reorder the candidate pool with **OpenAI embeddings** (same API key as LLM ask), then run lexical diversify. No vector database—vectors live only in memory for that query. |

Queries are tokenized consistently (Unicode word chars, English stopwords
dropped). **`retrieve`** is the best debug command when answers look wrong.

---

## 9. Ask: heuristic vs LLM

```bash
uv run knowledge-compiler ask "your question"
```

Default **`ask`** stitches a short answer from the **same** context snippets
using a **deterministic heuristic** (sentence overlap with query terms).
**Citations** always point to retrieved chunks.

Use **`--max-chars`**, **`--max-tokens`**, and **`--embed-rerank`** on **`ask`** the same
way as on **`context`** / **`retrieve`** so retrieval and context match your intent
before synthesis.

Optional **model-assisted wording**:

```bash
export KNOWLEDGE_COMPILER_OPENAI_API_KEY=sk-...
uv run knowledge-compiler ask "your question" --llm
# optional: --llm-model … or set KNOWLEDGE_COMPILER_LLM_MODEL
```

Uses an OpenAI-compatible **`/v1/chat/completions`** endpoint (override base URL
with **`KNOWLEDGE_COMPILER_OPENAI_BASE_URL`**). **Citations are unchanged**; only
the prose is synthesized. `last-answer.json` records **`synthesis`**: `heuristic`,
`openai-chat`, or `none` when no evidence.

Embedding rerank uses **`/v1/embeddings`** with **`KNOWLEDGE_COMPILER_EMBEDDING_MODEL`**
(default **`text-embedding-3-small`**).

---

## 10. Inspect, trace, and runs

```bash
uv run knowledge-compiler inspect workspace
uv run knowledge-compiler inspect topic <topic-id>
uv run knowledge-compiler inspect chunk <chunk-id>
```

**`inspect workspace`** shows document/chunk/topic counts and **theme** count;
with multiple sources it lists **`Sources (N): …`**.

```bash
uv run knowledge-compiler trace
```

Uses **`last-answer.json`**. For an older **`ask`** after more queries:

```bash
uv run knowledge-compiler runs
uv run knowledge-compiler trace --run <run-id-or-prefix>
```

**`runs`** prints **`run_id` first** on each line. Only **`ask`** runs recorded
after citation storage support **`trace --run`**; re-run **`ask`** if needed.

---

## 11. Good habits and debugging order

When an answer is weak, work **upstream**:

1. Did **`ingest`** see the right files?
2. Did **`compile`** produce expected topics/claims?
3. Does **`retrieve`** return the right chunks?
4. Does **`context`** select the right passages?
5. What does **`trace`** show was cited?

Separating “what the model said” from “what evidence existed” is the point of the
tool.

---

## 12. Troubleshooting

**Empty retrieval.** Run **`index`** after ingest/compile; check files under
`workspace/state/` exist; try **`--match or`** or a shorter query.

**`ingest-x-bookmarks` 403.** You need OAuth **2.0 user** context, not OAuth 1.0a
and not app-only Bearer. See §14.

**`ask --llm` errors.** Confirm **`KNOWLEDGE_COMPILER_OPENAI_API_KEY`**, network
access, and that the base URL serves **`/v1/chat/completions`**.

**`trace --run` fails on old history.** Older **`query-runs.jsonl`** lines may lack
stored citation ids; run a fresh **`ask`**.

---

## 13. Limitations

Retrieval is **lexical** (BM25 + diversification) unless you opt into **`--embed-rerank`**
(in-memory OpenAI embeddings, still no vector DB). Context uses **characters**
and optional **`--max-tokens`** with **tiktoken**; it is not guaranteed to match every
vendor tokenizer exactly. Compile is **one topic per document** with simple
claims; themes and cross-links are **keyword overlap**, not curated ontologies.
There is **no hosted UI** and **no connector marketplace**—only the connectors
shipped in this repo.

The design favors **traceability** over pretending to be a full enterprise KG
platform.

---

## 14. X bookmarks: auth notes (ES)

Necesitas un token **OAuth 2.0 de usuario** (flujo authorization code + PKCE) con
`tweet.read`, `users.read` y `bookmark.read`, guardado en
`KNOWLEDGE_COMPILER_X_ACCESS_TOKEN`. La API de X **no acepta OAuth 1.0a** en el
endpoint de bookmarks (403 “Unsupported Authentication”); las cuatro claves
OAuth 1.0a del portal **no sustituyen** un user token OAuth 2. El Bearer “solo
aplicación” tampoco sirve para `/users/me` ni bookmarks.

Variables recomendadas: copia **`.env.example`** a **`.env`** en la raíz del
proyecto (o exporta en la shell). Usa **`knowledge-compiler -p ~/tu-repo …`** si
el corpus no vive en el directorio actual.
