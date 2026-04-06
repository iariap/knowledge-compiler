---
name: ingest-compile-local-corpus
description: Ingest a local corpus, compile Markdown knowledge artifacts, and build the local search index. Use when the user wants to refresh the project workspace from local files, rebuild artifacts, or prepare the corpus for grounded queries.
---

# Ingest Compile Local Corpus

## Project root

The CLI resolves `workspace/` under a **project root**. By default that is the
current working directory. To pin a different root (for example a dedicated
corpus run directory), pass **`-p` / `--project-root`** immediately after
`knowledge-compiler` and **before** the subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`** for the shell session. Precedence:
**`--project-root`**, then **`KNOWLEDGE_COMPILER_ROOT`**, then **cwd**.

Run `uv` from the `knowledge-compiler` checkout so the package resolves; `-p`
only chooses where `workspace/` is written, not where Python finds the tool.

Paths below are relative to the chosen project root.

## Workflow

```bash
uv run knowledge-compiler ingest <input-dir>
uv run knowledge-compiler compile
uv run knowledge-compiler index
```

To **add** a folder corpus without wiping another source (for example bookmarks
already ingested), use **`ingest <dir> --merge`**. For single pages, **`ingest-url <url> --merge`**.

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root ingest <input-dir>
uv run knowledge-compiler -p /path/to/project-root compile
uv run knowledge-compiler -p /path/to/project-root index
```

## Verification

- Check `workspace/state/ingest-manifest.json`
- Check `workspace/compiled/compile-manifest.json` (includes **themes** when
  compile has run)
- Check `workspace/indexes/retrieval.db`

## Notes

- Use this only with workflows already implemented in the project.
- Prefer rebuilding the index after each successful compile.
