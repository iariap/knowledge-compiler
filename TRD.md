# Technical Requirements Document: knowledge-compiler

**Version:** 0.1.0 (aligned with package version)  
**Status:** Active — describes the current MVP slice as implemented in this repository.  
**Audience:** Engineers extending the pipeline, reviewers assessing design fit, and operators running the CLI in production-like local workflows.

This document states **what the system must do** and **how it is constrained**, grounded in the current code and persisted artifacts. It is the engineering counterpart to `README.md` (project intent and architecture narrative) and `practical-guide.md` (hands-on usage). When those sources disagree with running code, **code and on-disk schemas win** until the docs are updated.

---

## 1. Purpose and scope

The product is a **local-first knowledge compiler**: it ingests source material, normalizes it into stable evidence units (chunks), compiles human-readable derived artifacts (topics, claims, relations), builds a **rebuildable** lexical search index, and supports **grounded** question answering where answers are tied to chunk-level citations.

**In scope for this TRD:** batch ingest (local paths, **HTTP(S) URL fetch**, X bookmarks), compile, SQLite FTS indexing, explicit retrieval (`EvidencePack`) with optional **embedding rerank** over the FTS candidate pool, bounded context assembly (`ContextPack`) with character and optional **tiktoken** token caps, grounded `ask` (heuristic default, optional LLM wording, same retrieval/context options as `context`), workspace persistence layout, CLI behavior, environment configuration, and traceability hooks (`inspect`, `trace`, `runs`).

**Explicitly out of scope for the current slice:** hosted multi-tenant services, plugin marketplaces, vector databases, graph query engines, background job runners, web UI, broad connector ecosystems, and tokenizer-accurate model context planning. These exclusions are deliberate product boundaries unless/until the roadmap changes.

---

## 2. Problem statement and product intent

Organizations and individuals increasingly rely on LLMs over private or curated corpora. Two recurring failures are loss of **reuse** (no durable, inspectable knowledge layer) and loss of **trust** (answers that cannot be mapped to source evidence).

This system must **prioritize provenance and inspectability** over breadth of features: every answer path should be explainable in terms of stored chunks and file artifacts, not opaque retrieval or hidden prompts alone.

---

## 3. Goals and non-goals

**Goals**

- **G1 — Artifact-first workflow:** Ingest → normalized state → compile → index → query, with manifests summarizing each phase.
- **G2 — Chunk as canonical evidence:** Retrieval, context budgeting, and citations reference stable chunk identities and source line ranges.
- **G3 — Determinism where feasible:** Stable IDs, ordered JSON/JSONL writes, reproducible chunking and compile passes given the same inputs and versions.
- **G4 — Thin orchestration:** The CLI wires user input to services; domain logic lives in dedicated modules with injectable storage (`WorkspaceStore`).
- **G5 — Typed contracts:** Domain payloads use Pydantic models for persisted artifacts and service boundaries.

**Non-goals (current)**

- **NG1:** A **primary** vector or hybrid retrieval store (embeddings are not the source of recall; FTS remains canonical). Learned cross-encoder rerankers are out of scope.
- **NG2:** Real-time sync, incremental index updates (full index rebuild is acceptable).
- **NG3:** General-purpose agent frameworks or tool-calling loops in the core product.
- **NG4:** Guaranteeing “correct” natural-language answers without evidence — the system must refuse or qualify when evidence is missing.

---

## 4. System context

The system runs as a **Python 3.14+** CLI on the operator’s machine. It reads and writes a **`workspace/`** directory under a configurable **project root**. Optional outbound HTTPS calls support **HTTP(S) URL ingest** (operator-chosen URLs), **X (Twitter) bookmarks** ingestion (user OAuth 2.0 token), **OpenAI-compatible embeddings** (optional rerank over FTS hits), and **optional** OpenAI-compatible chat completion for answer wording.

No inbound network surface is required for core operation; network use is opt-in per command and environment variables.

---

## 5. Architectural requirements

**AR1 — Layering.** The implementation SHALL maintain separation consistent with the repository layout:

| Layer | Responsibility |
|--------|----------------|
| `schemas/` | Frozen (or intentionally mutable) Pydantic models for domain and persisted shapes |
| `connectors/` | Source adapters: `LocalFilesConnector` and `XBookmarksConnector` implement the `Connector` protocol; **URL ingest** uses `url_fetch.py` (fetch + normalize into documents/chunks, wired from `services/ingest_url.py`) |
| `ingestion/` | Discovery, normalization, chunking |
| `compile/` | Normalized state → topics, claims, relations, themes, cross-links |
| `retrieval/` | SQLite FTS index, query tokenization, lexical rerank/diversify, optional OpenAI embedding rerank (`embedding_rerank.py`, `openai_embeddings.py`) |
| `context/` | EvidencePack → ContextPack under character and optional token budget (`token_counter.py`) |
| `services/` | Use cases invoked by the CLI |
| `storage/` | `WorkspaceStore` persistence and loads |
| `cli.py` | Typer entrypoints only; no embedded business rules beyond validation and messaging |

**AR2 — Dependency direction.** Services depend on `WorkspaceStore` and pure functions in domain modules; domain modules SHALL NOT import the CLI.

**AR3 — Index disposability.** The retrieval database SHALL be regenerable from `workspace/state/chunks.jsonl` via the `index` command without manual migration steps for this MVP.

---

## 6. Project root and workspace

**WR1 — Project root resolution.** The effective project root SHALL be resolved in order: CLI `--project-root` / `-p`, then environment variable `KNOWLEDGE_COMPILER_ROOT`, then current working directory.

**WR2 — Environment loading.** On CLI startup, a `.env` file SHALL be loaded from the resolved project root via `python-dotenv`, without overwriting variables already set in the process environment.

**WR3 — Workspace directories.** Under `workspace/`, the system SHALL use:

- `raw/` — reserved for future raw retention; created eagerly.
- `state/` — normalized ingest outputs, query-time state files.
- `compiled/` — compile outputs (Markdown topics, JSON/L manifests).
- `indexes/` — `retrieval.db` (SQLite FTS5).

**WR4 — Multi-source ingest.** When `ingest`, **`ingest-url`**, or `ingest-x-bookmarks` runs with **`--merge`**, rows for other `source_id` values SHALL be preserved; the incoming connector replaces only its own source’s documents and chunks. Without `--merge`, the normalized bundle for state files written by ingest SHALL represent the single ingest run (replacement behavior).

---

## 7. Functional requirements — ingestion

**ING1 — Local file connector.** The local files connector SHALL recursively discover supported extensions under the given directory: `.md`, `.txt`, `.html`, `.htm`.

**ING2 — HTML handling.** HTML ingestion SHALL strip tags and script/style content to normalized plain text using standard-library facilities; it is not required to implement readability-style boilerplate removal.

**ING3 — Chunking.** Documents SHALL be chunked deterministically with a maximum chunk size of **1,200 characters** (`MAX_CHUNK_CHARS`), merging paragraphs until the budget would be exceeded, then starting a new chunk. Chunk IDs and ordinals SHALL be stable functions of document identity and content placement as implemented in `ingestion/chunking.py`.

**ING4 — Persisted ingest artifacts.** A successful ingest SHALL write:

- `workspace/state/sources.json` — JSON array of `Source` records.
- `workspace/state/documents.jsonl` — one `Document` per line.
- `workspace/state/chunks.jsonl` — one `Chunk` per line.
- `workspace/state/ingest-manifest.json` — `IngestManifest` with counts and `source_ids`.

**ING5 — X bookmarks connector.** When `KNOWLEDGE_COMPILER_X_ACCESS_TOKEN` is set to a valid OAuth 2.0 user access token with appropriate scopes, `ingest-x-bookmarks` SHALL call X API v2 bookmarks endpoints over HTTPS, map each bookmark to a text document (preferring `note_tweet.text` when present), and feed the result through the same normalization/chunking path as local files. The CLI SHALL surface configuration or permission errors as non-zero exit with a clear message.

**ING6 — X pagination controls.** `ingest-x-bookmarks` SHALL honor `--max-pages` and `--page-size` (1–100) as implemented, allowing bounded fetches for testing or large libraries.

**ING7 — URL fetch connector.** The `ingest-url` command SHALL accept one or more **http** or **https** URLs, perform GET requests with a fixed **User-Agent** (`knowledge-compiler/0.1 …`), enforce a **45 s** timeout and a **2,000,000-byte** response body cap (refuse larger bodies), and decode the body as UTF-8 with replacement on errors. When `Content-Type` or a quick sniff indicates **HTML**, the body SHALL be converted with the same HTML-to-plain pipeline as local `.html` ingest (`html_to_plain_text` + `normalize_text`); otherwise the normalized text SHALL be treated as plain. The connector SHALL use a stable synthetic `Source` with `source_id` **`url-fetch`** and `source_type` **`url_fetch`**. Each URL SHALL become one `Document` with `absolute_path` set to the URL, `relative_path` of the form `url/<16-hex-of-url-sha256>.txt`, `document_id` derived from a hash of the **extracted body text**, and chunks produced by the standard `chunk_document` path. Empty extractable text SHALL be a hard error for that URL. Network and HTTP errors SHALL surface as non-zero CLI exit with a readable message.

---

## 8. Functional requirements — compile

**CMP1 — Topic per document.** The compile pass SHALL produce one primary topic per ingested document, with Markdown under `workspace/compiled/topics/<topic_id>.md` and metadata in `workspace/compiled/topics.json`.

**CMP2 — Claims and relations.** The compile pass SHALL emit `claims.jsonl` and `relations.jsonl` with simple extracted statements and links as implemented in `compile/pipeline.py` (conservative, not a full IE pipeline).

**CMP3 — Lexical themes.** The compile pass SHALL run a deterministic lexical theme clustering pass (Jaccard-style overlap on titles/summaries), record `theme_id` / `theme_label` on topic records when applicable, and include theme metadata in `compile-manifest.json` (`themes`, `theme_clustering` version identifier).

**CMP4 — Cross-topic links.** The compile pass SHALL add lexical cross-topic relations with predicate `lexically_related_to` where overlap rules match, with ids such as `xref-<topic-a>-to-<topic-b>`, and SHALL record counts in `compile-manifest.json` (e.g. `lexical_cross_topic_links`, `cross_topic_mode`).

**CMP5 — Manifest.** `compile-manifest.json` SHALL summarize `topic_count`, `claim_count`, `relation_count`, and theme/cross-link fields produced by the run.

---

## 9. Functional requirements — indexing

**IDX1 — FTS5 schema.** The index SHALL be a SQLite virtual table `chunks_fts` using FTS5 with columns: `chunk_id`, `document_id`, `relative_path`, `start_line`, `end_line` as **UNINDEXED** metadata, and `text` indexed for search.

**IDX2 — Rebuild semantics.** `index` SHALL drop and recreate `chunks_fts` and repopulate from all chunks in `workspace/state/chunks.jsonl`.

**IDX3 — Search query.** Search SHALL use BM25 ranking via `bm25(chunks_fts)` in SQL as implemented in `SqliteChunkIndex.search`.

---

## 10. Functional requirements — retrieval and query-time

**RET1 — Tokenization consistency.** Query text SHALL be tokenized with the same Unicode-aware rules for FTS match expression building, lexical overlap scoring, and heuristic answer sentence selection (`retrieval/query_tokens.py`).

**RET2 — Match modes.** Retrieval SHALL support combining remaining query terms with FTS **AND** (default) or **OR** when `--match and|or` is set, mapped to `MatchMode`.

**RET3 — Candidate pool.** The raw FTS fetch size SHALL default to `max(limit * 6, 32)` unless overridden by `--candidate-pool`, clamped between the requested final `limit` and **200**.

**RET4 — Lexical rerank and diversify.** After the FTS candidate list is built, hits SHALL be reranked by `BM25_score + 0.12 * lexical_overlap(term_set, hit.text)` and diversified so that, in the first pass, at most `--max-per-document` chunks per `document_id` are selected; a second pass MAY relax the cap to fill up to `limit`.

**RET4b — Optional embedding rerank.** When `--embed-rerank` is set on `retrieve`, `context`, or `ask`, the system SHALL require `KNOWLEDGE_COMPILER_OPENAI_API_KEY`, call the OpenAI-compatible **`POST /v1/embeddings`** endpoint at `KNOWLEDGE_COMPILER_OPENAI_BASE_URL` (same base as chat), batching the **query string** and each hit’s `text` truncated to **8,000 characters** (`_MAX_EMBED_CHARS`). It SHALL reorder hits by **cosine similarity** between query and chunk vectors, and replace each hit’s `score` with that similarity **before** the diversify step in **RET4**. The embedding model SHALL default to **`text-embedding-3-small`** or `KNOWLEDGE_COMPILER_EMBEDDING_MODEL` when set.

**RET5 — EvidencePack.** `retrieve` SHALL persist `EvidencePack` to `workspace/state/last-evidence-pack.json`, including `chunk_ids`, `hits`, overlapping `topic_ids` and `claim_ids` derived from compiled artifacts, plus metadata: `match_mode`, `ranking_strategy` (**`bm25_lexical_diversify`** by default, or **`openai_embed+bm25_lexical_diversify`** when embedding rerank ran), **`candidate_hits_fetched`** (count of raw FTS rows returned for the pool, before embedding reorder), and `max_chunks_per_document`.

**RET6 — ContextPack.** `context` (and the context stage of `ask`) SHALL build a `ContextPack` with base selection strategy **`query-aware-multi-snippet-v2`**, append **`+token_cap`** when `--max-tokens` is set, enforce `--max-chars` (50–20,000 on CLI), prefer query-aware sentence-level snippets from evidence hits, and deduplicate normalized snippet bodies. Token measurement SHALL use **`tiktoken` encoding `cl100k_base`** via `context/token_counter.py` when the encoder loads successfully; on encoder failure the same module SHALL fall back to a character heuristic (~4 chars per token). The pack SHALL set `estimated_input_tokens` from per-snippet token counts plus overhead. When `max_tokens` is set, each accepted snippet SHALL be clipped to fit the remaining token budget (including a small per-snippet overhead modeled in code). Persisted fields SHALL include `max_tokens`, `used_tokens`, and the usual `used_chars` / `max_chars`. Output SHALL be written to `workspace/state/last-context-pack.json`.

**RET7 — Query run history.** Each `retrieve`, `context`, and `ask` invocation SHALL append a `QueryRun` record to `workspace/state/query-runs.jsonl` with stable `run_id`, timestamps, counts, and optional context/answer fields as implemented in `services/runs.py`.

---

## 11. Functional requirements — grounded answering

**ASK1 — Evidence-only answers.** `ask` SHALL build a `ContextPack` via the same retrieval path as `context` (including shared flags: `--limit`, `--match`, `--candidate-pool`, `--max-per-document`, **`--max-chars`**, **`--max-tokens`**, **`--embed-rerank`**), then:

- If no snippets: return explicit “no evidence” messaging, empty citations, persist `last-answer.json`, and record the run.
- If snippets: produce `answer_text` and citations for each context snippet’s chunk (path and line range from snippet metadata).

**ASK2 — Default synthesis.** Without `--llm`, answer text SHALL be produced by the deterministic heuristic in `services/ask.py` (query-aware sentence picking, up to three sentences, deduplicated).

**ASK3 — Optional LLM synthesis.** With `--llm`, when `KNOWLEDGE_COMPILER_OPENAI_API_KEY` is set, the system SHALL call `POST {base}/v1/chat/completions` on an OpenAI-compatible API with low temperature (~0.2), using a system prompt that restricts the model to provided excerpts keyed by `chunk_id`. Citations SHALL still reflect retrieved chunks, not model-invented locations. `QueryAnswer.synthesis` SHALL indicate `openai-chat` vs `heuristic` / `none`.

**ASK4 — Last answer persistence.** `ask` SHALL write `workspace/state/last-answer.json` as a serialized `QueryAnswer`.

**ASK5 — Trace.** `trace` without `--run` SHALL replay `last-answer.json` and load cited chunk bodies from `chunks.jsonl`. `trace --run <id>` SHALL resolve an `ask` entry from `query-runs.jsonl` by exact or unique prefix, require stored `citation_chunk_ids`, and reconstruct citations and chunk text accordingly.

---

## 12. Functional requirements — inspection

**INS1 — Workspace summary.** `inspect workspace` SHALL report counts from ingest/compile manifests, paths to state/compiled/indexes, multi-source ids when present, and summarize last evidence/context packs when valid on disk.

**INS2 — Chunk and topic inspection.** `inspect chunk <id>` and `inspect topic <id>` SHALL load from workspace state/compiled files and SHALL exit non-zero on unknown ids.

**INS3 — Runs listing.** `runs` SHALL print recent query runs newest-first, including run id, command, query, hit/chunk/topic/claim counts, context character usage when recorded, and answer preview/text fields when present.

---

## 13. Data integrity and schema contracts

**DS1 — Serialization.** JSON files SHALL be written with sorted keys and indentation (2 spaces) as implemented in `WorkspaceStore._write_json`. JSONL SHALL be one JSON object per line, sorted keys per object.

**DS2 — Model validation.** Loading persisted artifacts SHALL use Pydantic validation; invalid on-disk state may cause commands to fail until the workspace is repaired or regenerated.

**DS3 — Core schema types (non-exhaustive).** The system relies on models including: `Source`, `Document`, `Chunk`, `ChunkProvenance`, `TopicRecord`, `TopicMarkdownArtifact`, `Claim`, `Relation`, `IngestManifest`, `CompileManifest`, `EvidencePack`, `ContextPack` (including optional **`max_tokens`** / **`used_tokens`**), `ContextSnippet`, `QueryAnswer`, `AnswerCitation`, `SearchHit`, `QueryRun`, `WorkspaceInspection`, etc., defined under `src/knowledge_compiler/schemas/`.

---

## 14. Non-functional requirements

**NFR1 — Language runtime.** The package requires **Python ≥ 3.14** as declared in `pyproject.toml`.

**NFR2 — Dependencies (runtime).** Runtime dependencies are **pydantic**, **python-dotenv**, **tiktoken**, **typer**; SQLite is via the standard library. There is no OpenAI **SDK** dependency — chat, embeddings, and URL fetch use **`urllib`**.

**NFR3 — Security and secrets.** Secrets (X user token, API keys) SHALL come from environment or `.env`; they SHALL NOT be written into committed artifacts. `.env` is gitignored by project convention.

**NFR4 — Privacy.** Default operation SHALL keep corpus and indexes on local disk. Optional network calls send HTTP GETs to **operator-supplied URLs**, X API traffic for bookmarks, and JSON payloads to the configured OpenAI-compatible host for **embeddings** and/or **chat** when those features are enabled.

**NFR5 — Performance.** No strict SLAs are defined for this MVP; full index rebuild and full corpus compile are acceptable batch operations. OpenAI-compatible **chat** and **embeddings** requests use a **120 s** timeout as implemented; URL ingest uses a **45 s** timeout per request.

**NFR6 — Observability.** Operators SHALL be able to trace answers to chunks via CLI `trace` and by reading JSON artifacts; query history SHALL be inspectable via `runs` and `query-runs.jsonl`.

**NFR7 — Testing.** The repository SHALL maintain automated tests (`pytest`) and static typing (`ty`) as the declared quality gates in `README.md`.

---

## 15. CLI surface (summary)

The installed console script is **`knowledge-compiler`**. Global option: `--project-root` / `-p`. Subcommands: **`ingest`**, **`ingest-url <url> [<url> …]`**, **`ingest-x-bookmarks`**, `compile`, `index`, `retrieve`, `context`, `ask`, `inspect` (with `workspace` | `chunk` | `topic`), `trace`, `runs`. Numeric and enum-like options SHALL enforce min/max as coded in `cli.py` (e.g. `limit` 1–20 for ask/context/retrieve; `max_chars` 50–20000 for **context** and **ask**; **`max_tokens`** 50–100_000 when passed to **context** or **ask**). **`retrieve`**, **`context`**, and **`ask`** SHALL accept **`--embed-rerank`** and SHALL fail fast with a clear message if the API key is missing when that flag is set.

---

## 16. External interfaces

**IF1 — X API v2 (bookmarks).** User-context OAuth 2.0 Bearer token; scopes include `tweet.read`, `users.read`, `bookmark.read`. The integration MUST NOT treat application-only Bearer tokens as sufficient for bookmarks.

**IF2 — OpenAI-compatible Chat Completions.** HTTPS POST to `/v1/chat/completions` with JSON body containing `model`, `messages`, `temperature`. Base URL and chat model overridden by `KNOWLEDGE_COMPILER_OPENAI_BASE_URL` and `KNOWLEDGE_COMPILER_LLM_MODEL` (or `--llm-model` on `ask`).

**IF3 — OpenAI-compatible Embeddings.** HTTPS POST to `/v1/embeddings` with JSON body containing `model` and `input` (list of strings). Used for **`--embed-rerank`**. Default embedding model: `KNOWLEDGE_COMPILER_EMBEDDING_MODEL` or **`text-embedding-3-small`**. Same `Authorization: Bearer` and base URL convention as chat.

---

## 17. Risks and limitations

Lexical retrieval can still miss paraphrases unless **`--embed-rerank`** is used; even then, recall is still FTS-bounded. Embedding rerank adds **latency and API cost** and sends chunk text to the configured provider. URL ingest fetches **untrusted remote content** chosen by the operator (appropriate for a local CLI, but not a safe primitive for unsupervised server-side crawling). Compile-time themes and cross-links are **explainable but coarse**; token caps depend on **tiktoken** when available. `ask --llm` can still hallucinate if the model disobeys instructions — operators should rely on citations and `trace` for verification. X API availability and policy are external dependencies.

---

## 18. Roadmap alignment (informative)

Probable evolution (from project README): richer compiled artifacts, better retrieval and evidence assembly, more connectors, optional deeper LLM layers — **without** abandoning chunk-grounded traceability.

---

## 19. Glossary

| Term | Meaning |
|------|--------|
| **Chunk** | Canonical evidence unit with text and provenance (path, line range, source). |
| **EvidencePack** | Explicit ranked retrieval result for a query. |
| **ContextPack** | Budgeted snippets selected from evidence for answering. |
| **Grounded answer** | Answer accompanied by citations to real chunks; may be heuristic or LLM-worded. |
| **Project root** | Directory containing `workspace/`. |

---

## 20. References

- `README.md` — product narrative, architecture diagrams, domain concept diagram.  
- `practical-guide.md` — operator workflows, examples, troubleshooting.  
- `pyproject.toml` — packaging, entry point, dev dependencies.  
- `.env.example` — environment variable template.
