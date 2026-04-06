---
name: review-query-history
description: Review the recent local query-time history for retrieve, context, and ask commands. Use when the user wants to see what queries were run recently, compare the retrieval and context steps, or understand how the current workspace has been queried.
---

# Review Query History

## Project root

Pass **`-p` / `--project-root`** before the subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`**, so history comes from that tree’s
`workspace/state/query-runs.jsonl`. Precedence: **`--project-root`**, then
**`KNOWLEDGE_COMPILER_ROOT`**, then **cwd**.

## Command

```bash
uv run knowledge-compiler runs
```

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root runs
```

Optional limit:

```bash
uv run knowledge-compiler -p /path/to/project-root runs --limit 20
```

## What it shows

The command shows the recent local history of `retrieve`, `context`, and `ask`
runs. It is useful when you want to see the path the user has taken through the
query workflow instead of only inspecting the very last answer.

## Notes

The history is local and append-only. It is not yet a full run-management system
or a complete audit log.
