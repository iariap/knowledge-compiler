---
name: retrieve-grounded-evidence
description: Retrieve the current evidence pack for a query from the local workspace without forcing an answer. Use when the user wants to inspect what chunks, topics, and claims the system found before or instead of running grounded answer synthesis.
---

# Retrieve Grounded Evidence

## Purpose

Use this workflow when the user wants to see what the system retrieved, not just
what it answered.

## Project root

Pass **`-p` / `--project-root`** before the subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`**, so `workspace/` matches the corpus the user cares
about. Precedence: **`--project-root`**, then **`KNOWLEDGE_COMPILER_ROOT`**, then
**cwd**. Artifact paths below are relative to that root.

## Command

```bash
uv run knowledge-compiler retrieve "<query>"
```

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root retrieve "<query>"
```

Optional retrieval tuning: **`--match and|or`** (FTS term combination),
**`--candidate-pool N`**, **`--max-per-document K`** (diversification). Defaults
match the README.

## What it gives you

The command returns the current query, match/ranking metadata, the number of
matching chunks, related topics and claims, and the ranked evidence hits with
source paths and line ranges.

It also writes the current evidence pack to:

```text
workspace/state/last-evidence-pack.json
```

## Notes

This command assumes the workspace has already been ingested, compiled, and
indexed.
