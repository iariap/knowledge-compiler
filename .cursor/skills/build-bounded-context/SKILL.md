---
name: build-bounded-context
description: Build a bounded context pack from the current retrieval layer without forcing a final answer. Use when the user wants to see the selected evidence that would feed grounded answering or later LLM synthesis.
---

# Build Bounded Context

## Purpose

Use this workflow when you want to inspect the selected evidence that fits
within the current context budget.

## Project root

Pass **`-p` / `--project-root`** before the subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`**, so context and evidence packs come from the
intended `workspace/`. Precedence: **`--project-root`**, then
**`KNOWLEDGE_COMPILER_ROOT`**, then **cwd**.

## Command

```bash
uv run knowledge-compiler context "<query>"
```

Optional limits and budget:

```bash
uv run knowledge-compiler context "<query>" --limit 5 --max-chars 1500
```

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root context "<query>" --max-chars 1500
```

The same retrieval flags as **`retrieve`** apply (`--match`, `--candidate-pool`,
`--max-per-document`, `--embed-rerank`). Use **`--max-tokens`** for a tiktoken-based
cap alongside **`--max-chars`**. Output includes **estimated tokens** next to the
character budget.

## What it does

The command retrieves evidence, applies a character budget, may include
multiple snippets when space allows, and stores the resulting context pack in:

```text
workspace/state/last-context-pack.json
```

## Notes

This command assumes the workspace has already been ingested, compiled, and
indexed.
