---
name: ask-grounded-question
description: Ask grounded questions against the local knowledge workspace using the built search index and return cited evidence. Use when the user wants to query the current corpus, inspect supporting chunks, or verify what evidence supports an answer.
---

# Ask Grounded Question

## Preconditions

- The workspace has already been ingested.
- The compile step has completed.
- The search index exists.

## Project root

Pass **`-p` / `--project-root`** before the subcommand, or set
**`KNOWLEDGE_COMPILER_ROOT`**, so answers and citations use the correct
`workspace/`. Precedence: **`--project-root`**, then
**`KNOWLEDGE_COMPILER_ROOT`**, then **cwd**.

## Workflow

```bash
uv run knowledge-compiler ask "<question>"
```

With an alternate project root:

```bash
uv run knowledge-compiler -p /path/to/project-root ask "<question>"
```

Optional: same retrieval flags as **`retrieve`** (`--match`, `--candidate-pool`,
`--max-per-document`). Optional **LLM wording**: **`ask --llm`** when
`KNOWLEDGE_COMPILER_OPENAI_API_KEY` is set (OpenAI-compatible chat); citations stay
tied to retrieved chunks.

## If The Index Is Missing

Rebuild the index for the same project root:

```bash
uv run knowledge-compiler -p /path/to/project-root index
```

## Expected Output

- grounded answer text
- citations with chunk IDs and source line ranges

## Notes

- This skill is for the currently implemented local grounded query flow.
- If no evidence is found, report that explicitly instead of inventing an answer.
