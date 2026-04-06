# Practical Guide

This file is the practical guide to using `knowledge-compiler`.

`README.md` explains the project itself: why it exists, how it is structured,
and what design principles shape it. This file is narrower and more practical.
It is meant to help you operate the tool, understand what each command is for,
and build good habits when working with a local knowledge corpus.

If you remember only one thing, remember this: the tool is not trying to hide
its workflow. It wants you to see the path from source files to evidence, from
evidence to selected context, and from selected context to answer.

## What The Tool Does In Practice

You point the tool at a folder that contains notes or documents. The tool reads
those files, turns them into deterministic chunks, compiles a first layer of
knowledge artifacts, builds a local search index, and then lets you query the
corpus in grounded ways.

The important difference from a normal “chat with files” workflow is that the
system keeps the intermediate steps visible. You can inspect what was ingested,
what was compiled, what was retrieved, what was selected into the answer
context, and what evidence was ultimately cited.

That makes it a much better fit for work where trust matters. If something
looks wrong, you can inspect the pipeline instead of guessing.

## What It Supports Right Now

At the moment the tool is intentionally narrow. It works with local `md` and
`txt` files, and it can optionally pull posts you have **saved on X** (API
bookmarks) if you configure an OAuth 2.0 user access token. It can ingest those
sources, compile them into a first layer of topic artifacts, index the chunks
with local SQLite full-text search, retrieve evidence, build a bounded context
selection, answer questions with citations, inspect stored artifacts, and trace
the most recent answer back to its chunks.

This means the workflow is already real, but still small. Aside from the
optional X bookmarks API path, there is no wider connector catalog yet, no web
UI, and no model-powered synthesis layer beyond the current grounded answer
path.

## The Mental Model

The easiest way to understand the tool is to think in stages, because each
stage answers a different practical question.

`ingest` answers: “How do my raw files become stable internal evidence?”

`ingest-x-bookmarks` answers: “How do the posts I saved on X become the same kind
of evidence, without exporting my whole account archive?”

`compile` answers: “What derived knowledge artifacts can the system make from
that evidence?”

`index` answers: “How does the system make canonical chunks searchable?”

`retrieve` answers: “What evidence seems relevant to this query?”

`context` answers: “Which part of that evidence actually fits into the current
working context?”

`ask` answers: “Given that selected context, what grounded answer can I return?”

`inspect` and `trace` are the trust-preserving commands. They help you move from
“the system said something” to “show me what it used and why.”

There is now also a `runs` command. It is simpler than a full run-management
system, but it gives you a local history of recent query-time steps so you are
not limited to whatever the tool happened to do last.

## Your First Run

If you want to understand the tool before using your own notes, start with the
fixture corpus already present in the repository.

Begin by syncing dependencies:

```bash
uv sync
```

Then run the full flow:

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

That sequence is the best way to learn the tool because each command exposes a
different layer of the pipeline.

## Using It With Your Own Notes

Once the sample flow makes sense, using your own corpus is straightforward.
Replace the fixture folder with your own directory:

```bash
uv run knowledge-compiler ingest /path/to/my-notes
uv run knowledge-compiler compile
uv run knowledge-compiler index
```

If your shell is not in the directory that should hold `workspace/`, either pass
`-p` / `--project-root` before the subcommand (for example
`knowledge-compiler -p ~/notes-repo ingest ~/notes-repo/inbox`) or export
`KNOWLEDGE_COMPILER_ROOT` to that project directory. The flag overrides the
environment variable for a single run; both override the current working
directory.

From that point on, you can query the corpus:

```bash
uv run knowledge-compiler retrieve "What did I write about API design?"
uv run knowledge-compiler context "What did I write about API design?"
uv run knowledge-compiler ask "What did I write about API design?"
```

For now, if your notes change, the normal refresh flow is simply to re-run
`ingest`, `compile`, and `index`.

## What Each Command Means

### `ingest`

Use `ingest` when the source folder is the thing that changed.

```bash
uv run knowledge-compiler ingest /path/to/my-notes
```

This command walks the directory, reads supported files (`md`, `txt`, `html`/`htm`
with simple tag stripping), normalizes the text, builds deterministic chunks, and
writes the normalized state into `workspace/state/`.

Add **`--merge`** when you already have another source in the workspace (for
example after `ingest-x-bookmarks`) and you want to add or refresh this folder
without dropping the other source’s documents.

You should think of this as the moment where raw files become canonical
evidence.

### `ingest-x-bookmarks`

Use this when your “notes” live in **X bookmarks** and you want them in the
compiler without the zip export.

```bash
# Variables en .env en la raíz del proyecto (recomendado) o export en la shell
uv run knowledge-compiler ingest-x-bookmarks
```

Necesitas un token **OAuth 2.0 de usuario** (flujo authorization code + PKCE)
con `tweet.read`, `users.read` y `bookmark.read`, guardado en
`KNOWLEDGE_COMPILER_X_ACCESS_TOKEN`. La API de X **no acepta OAuth 1.0a** en el
endpoint de bookmarks (responde 403 “Unsupported Authentication”); por eso las
cuatro claves OAuth 1.0a del portal **no sirven** para este comando aunque estén
bien configuradas. El Bearer “solo aplicación” tampoco vale. El tool llama a la
API por HTTPS, arma un documento por post guardado y lo parte en chunks como el
resto de fuentes.

**Texto completo vs recortes.** El cuerpo guardado por post es el `text` que
devuelve la API para ese bookmark; el ingest **no** recorta ese campo. Aun así,
X a veces entrega **texto acortado** en posts muy largos si no pides campos extra
de long-form (el conector actual solo pide `text` estándar). El **título** del
tema en compile sí se acorta (~80 caracteres) para nombres de archivo; el texto
completo sigue en los chunks. El **resumen** del topic en compile es un extracto
corto (~240 caracteres), no el post entero. En `context` y `ask` solo verás
fragmentos que quepan en el presupuesto de caracteres.

Use `--max-pages` if you want to cap how many paged API calls run (helpful when
experimenting). By default each run **replaces** the whole `workspace/state`
bundle. Use **`--merge`** to refresh only the bookmark source and keep documents
from a prior folder `ingest` (or the other way around: folder ingest with
`--merge` after bookmarks).

### `compile`

Use `compile` after ingesting content and you want the first derived knowledge
layer on top of the normalized chunks.

```bash
uv run knowledge-compiler compile
```

This command reads the normalized state and creates topic pages, claims,
relations, and compile metadata under `workspace/compiled/`. It also assigns
**lexical themes**: topics that share enough keywords in title+summary are grouped,
with labels derived from frequent terms (no vectors). Check `compile-manifest.json`
(`themes`) and each topic’s **Theme** section in Markdown; `topics.json` includes
`theme_id` and `theme_label`.

**Cross-topic links:** when two different topics overlap enough in title+summary
vocabulary, compile emits `lexically_related_to` rows in `relations.jsonl`
(`xref-…` ids). The manifest field `lexical_cross_topic_links` counts them.

Right now the compile step is intentionally conservative beyond that: it does not
build a hand-curated ontology.

### `index`

Use `index` when you want retrieval to reflect the current chunk state.

```bash
uv run knowledge-compiler index
```

This command rebuilds the SQLite full-text index from the chunk artifacts. If
the corpus changed, or if you re-ran ingest and compile, index again before
querying.

### `retrieve`

Use `retrieve` when you want to inspect what the system found before asking it
to form an answer.

```bash
uv run knowledge-compiler retrieve "What did I write about API design?"
```

This command assembles the current `EvidencePack`. It shows the query, how many
chunks matched, how many related topics and claims overlap with those chunks,
and the actual retrieved hit snippets with source line ranges.

Your query string is tokenized consistently for search, context selection, and
the bundled answer heuristic: word characters (including letters outside ASCII)
are kept, punctuation mostly acts as a separator, common English stopwords are
dropped. By default those terms are **AND**ed in FTS; use `--match or` if any
term should match. The CLI fetches a **candidate pool** (see `--candidate-pool`),
then **reranks** (BM25 plus lexical overlap) and **limits chunks per document**
(`--max-per-document`, default 2) so one source does not dominate the list.

Sentence selection inside chunks uses the same token shape for overlap, so a
query like `foo bar` still lines up with `foo-bar` in the source text.

This is one of the best debugging commands in the system. If retrieval is wrong,
everything after it will also be wrong.

### `context`

Use `context` when you want to inspect the selected evidence that would actually
feed answer generation.

```bash
uv run knowledge-compiler context "What did I write about API design?"
```

You can also change the budget to see how the selection gets trimmed:

```bash
uv run knowledge-compiler context "What did I write about API design?" --limit 5 --max-chars 800
```

This command writes a `ContextPack`. That pack is the tool’s answer to the
question: “Given the evidence we found, what exact evidence slice should we work
with right now?” It may contain **multiple snippets** when the character budget
allows; the output includes an **estimated token** count (rough heuristic) next to
the character budget. The same `--match`, `--candidate-pool`, and
`--max-per-document` flags as `retrieve` apply.

### `ask`

Use `ask` when you want a grounded answer with citations.

```bash
uv run knowledge-compiler ask "What did I write about API design?"
```

This command builds on the earlier steps. It retrieves evidence (with the same
optional retrieval flags as `retrieve` / `context`), builds a bounded context
pack, and forms an answer from the selected snippets. If the system cannot find
supporting evidence, it should say so explicitly.

In practice, `ask` is the “normal user” query command, but the best habit early
on is to pair it with `retrieve` and `trace` so you can understand why you got
the answer you got.

### `inspect`

Use `inspect` when you want to understand stored state directly instead of
reading raw JSON files by hand.

To inspect the workspace as a whole:

```bash
uv run knowledge-compiler inspect workspace
```

To inspect one topic:

```bash
uv run knowledge-compiler inspect topic <topic-id>
```

To inspect one chunk:

```bash
uv run knowledge-compiler inspect chunk <chunk-id>
```

`inspect workspace` includes a **themes** count when compile has run (lexical
theme groups from the manifest).

This is useful when you want to move from “the tool said something” to “show me
the underlying artifact.”

### `trace`

Use `trace` after `ask`, when you want to see which chunks supported an answer.
By default it follows `workspace/state/last-answer.json` (the latest `ask`).

```bash
uv run knowledge-compiler trace
```

If you ran more queries afterward, list ids with `runs`, then trace the older
`ask` by id (full id or a unique prefix):

```bash
uv run knowledge-compiler trace --run ask-1a2b3c4d5e6f
```

Older lines in `query-runs.jsonl` from before citation storage may not support
`--run`; run a fresh `ask` if you need a traceable snapshot.

This command is the easiest way to keep the system honest. If the answer feels
surprising, vague, or too confident, `trace` lets you inspect the cited chunk
content directly.

### `runs`

Use `runs` when you want to review the recent local query history instead of
looking only at the current “last” artifacts.

```bash
uv run knowledge-compiler runs
```

Each line begins with a **run id** (use it with `trace --run` for past `ask`
runs), then the command, query, and counts. It is useful when you want to compare
what you queried, what the system retrieved, how much context it selected, and
what kind of answer surface it produced. For `context` and `ask`, the same
`context_chars` field reflects how many characters were included after the budget
was applied. When topics or claims are linked to the retrieved chunks, the
summary line also includes `topics` and `claims` counts.

## What Gets Written To Disk

The tool stores its work under `workspace/`.

`workspace/state/` holds normalized state and query-time artifacts. This is
where you will find:

- `sources.json`, which records the current source configuration
- `documents.jsonl`, which records normalized documents
- `chunks.jsonl`, which records canonical evidence chunks
- `ingest-manifest.json`, which summarizes ingest output
- `last-evidence-pack.json`, which stores the most recent retrieval result
- `last-context-pack.json`, which stores the most recent bounded context
- `last-answer.json`, which stores the most recent answer
- `query-runs.jsonl`, which stores recent local query-time history

`workspace/compiled/` holds derived knowledge artifacts. This is where you will
find:

- `topics/<topic>.md`, the generated Markdown topic pages
- `topics.json`, the typed topic records
- `claims.jsonl`, the current claim artifacts
- `relations.jsonl`, the current relation artifacts
- `compile-manifest.json`, the summary of compile output

`workspace/indexes/` holds the search index:

- `retrieval.db`, the local SQLite FTS database

## Good Habits While Using The Tool

The most useful habit is to separate “answering” from “understanding.” If you
get an answer that feels weak, do not immediately tweak the query and hope for a
miracle. First run `retrieve` and `context` to see what evidence the system is
actually working with. Then run `trace` after `ask` to see what it cited.

Another good habit is to re-run `index` after the corpus changes. Since the
current system is local and explicit, it rewards small, disciplined refresh
flows.

It is also worth using `inspect workspace` regularly. It gives you a quick sense
of whether the current artifact state matches what you think the system should
contain.

## Current Limitations

The current workflow is intentionally narrow. Only local `md` and `txt` files
are supported right now. The compile step is simple and largely document-based.
Retrieval is lexical, not semantic. Context selection is query-aware, but still
simple and bounded by character budget rather than real token accounting. Trace
is focused on the most recent answer, and the query history is still a simple
local append-only log rather than a richer run-management system.

That means the system is already useful for local, inspectable experiments, but
it is not yet a full production knowledge platform.

## If Something Looks Wrong

If the tool gives you a weak answer, the right debugging order is usually:

First, check whether `ingest` actually saw the files you expected.

Then check whether `compile` produced the topic and claim artifacts you expected.

Then check whether `retrieve` found the evidence you expected.

Then check whether `context` selected the right part of that evidence.

Finally, check `trace` to see exactly what the answer cited.

That order mirrors the system itself, which is why it works well.
