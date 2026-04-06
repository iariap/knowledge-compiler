---
name: inspect-and-trace-workspace
description: Inspect the current workspace artifacts and trace the last grounded answer back to cited chunks. Use when the user wants to understand what the compiler produced, inspect a topic or chunk, or verify the evidence behind the most recent answer.
---

# Inspect And Trace Workspace

## Project root

Pass **`-p` / `--project-root`** before each subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`**, so inspect and trace read the intended
`workspace/`. Precedence: **`--project-root`**, then
**`KNOWLEDGE_COMPILER_ROOT`**, then **cwd**.

## Inspect the workspace

Use these commands when you need to understand the current artifact state:

```bash
uv run knowledge-compiler inspect workspace
uv run knowledge-compiler inspect topic <topic-id>
uv run knowledge-compiler inspect chunk <chunk-id>
```

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root inspect workspace
uv run knowledge-compiler -p /path/to/project-root inspect topic <topic-id>
uv run knowledge-compiler -p /path/to/project-root inspect chunk <chunk-id>
```

`inspect workspace` reports a **themes** count when the compile manifest lists
lexical theme groups.

## Trace grounded answers

Most recent **`ask`** (reads `last-answer.json`):

```bash
uv run knowledge-compiler trace
```

A specific past **`ask`** (id from **`runs`**, full id or unique prefix):

```bash
uv run knowledge-compiler trace --run ask-abc123deadbeef
```

With an alternate project root, prefix **`-p`** on the same line as **`trace`**.

## Notes

These commands work with already-generated local artifacts. If the workspace has
not been ingested, compiled, indexed, and queried yet, rebuild it first with the
existing ingest, compile, index, and ask workflow (using the same **`-p`** or
**`KNOWLEDGE_COMPILER_ROOT`** as here).
