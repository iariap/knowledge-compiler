from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from knowledge_compiler.config import Settings
from knowledge_compiler.env_file import load_local_env
from knowledge_compiler.services import (
    ask_workspace,
    build_search_index,
    build_query_context,
    compile_workspace,
    ingest_local_files,
    ingest_x_bookmarks,
    inspect_chunk,
    inspect_topic,
    inspect_workspace,
    list_query_runs,
    retrieve_evidence,
    trace_ask_run,
    trace_last_answer,
)
from knowledge_compiler.storage import WorkspaceStore

app = typer.Typer(add_completion=False, no_args_is_help=True)
inspect_app = typer.Typer(add_completion=False, no_args_is_help=True)

ProjectRootOption = Annotated[
    Path | None,
    typer.Option(
        "--project-root",
        "-p",
        help="Project root (directory that contains workspace/). Overrides KNOWLEDGE_COMPILER_ROOT and cwd.",
    ),
]


def _store(ctx: typer.Context) -> WorkspaceStore:
    settings: Settings = ctx.obj["settings"]
    store = WorkspaceStore(settings)
    store.ensure_workspace()
    return store


@app.callback()
def cli(ctx: typer.Context, project_root: ProjectRootOption = None) -> None:
    """Knowledge Compiler command group."""
    load_local_env(project_root)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = Settings.from_project_root(project_root)


app.add_typer(inspect_app, name="inspect")


@app.command("ingest")
def ingest(
    ctx: typer.Context,
    input_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    merge: bool = typer.Option(
        False,
        "--merge",
        help="Add or replace this source's documents without dropping other sources.",
    ),
) -> None:
    store = _store(ctx)
    manifest = ingest_local_files(input_path=input_path, store=store, merge=merge)

    typer.echo(
        f"Ingested {manifest.document_count} documents and {manifest.chunk_count} chunks into "
        f"{store.settings.state_dir}."
    )


@app.command("ingest-x-bookmarks")
def ingest_x_bookmarks_command(
    ctx: typer.Context,
    max_pages: int | None = typer.Option(
        None,
        "--max-pages",
        min=1,
        help="Stop after this many bookmark API pages (default: fetch all pages).",
    ),
    page_size: int = typer.Option(
        100,
        "--page-size",
        min=1,
        max=100,
        help="Bookmarks per request (X API allows at most 100).",
    ),
    merge: bool = typer.Option(
        False,
        "--merge",
        help="Add or replace bookmark documents without dropping other ingested sources.",
    ),
) -> None:
    """Ingest posts you saved on X via API v2 bookmarks (OAuth 2.0 user token required)."""
    store = _store(ctx)
    try:
        manifest = ingest_x_bookmarks(
            store=store,
            max_pages=max_pages,
            page_size=page_size,
            merge=merge,
        )
    except (OSError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(
        f"Ingested {manifest.document_count} bookmarked posts and {manifest.chunk_count} chunks into "
        f"{store.settings.state_dir}."
    )


@app.command("compile")
def compile_command(ctx: typer.Context) -> None:
    store = _store(ctx)
    manifest = compile_workspace(store=store)

    typer.echo(
        f"Compiled {manifest.topic_count} topics, {manifest.claim_count} claims, and "
        f"{manifest.relation_count} relations into {store.settings.compiled_dir}."
    )
    if manifest.themes:
        typer.echo(
            f"Lexical themes: {len(manifest.themes)} groups ({manifest.theme_clustering}). "
            f"See compile-manifest.json and topic pages."
        )


@app.command("index")
def index_command(ctx: typer.Context) -> None:
    store = _store(ctx)
    chunk_count = build_search_index(store=store)
    typer.echo(
        f"Indexed {chunk_count} chunks into {store.settings.indexes_dir / 'retrieval.db'}."
    )


@app.command("ask")
def ask_command(
    ctx: typer.Context,
    query: str = typer.Argument(...),
    limit: int = typer.Option(5, min=1, max=20),
    match_mode: str = typer.Option(
        "and",
        "--match",
        help="How FTS combines query terms: and (all) or or (any).",
    ),
    candidate_pool: int | None = typer.Option(
        None,
        "--candidate-pool",
        min=5,
        max=200,
        help="Raw hits to score before diversification (default: max(limit*6, 32)).",
    ),
    max_per_document: int = typer.Option(
        2,
        "--max-per-document",
        min=1,
        max=20,
        help="At most this many chunks per document in the final ranked list.",
    ),
) -> None:
    store = _store(ctx)
    try:
        answer = ask_workspace(
            query=query,
            store=store,
            limit=limit,
            match_mode=match_mode,
            candidate_pool=candidate_pool,
            max_chunks_per_document=max_per_document,
        )
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(answer.answer_text)
    if answer.citations:
        typer.echo("")
        typer.echo("Citations:")
        for citation in answer.citations:
            typer.echo(
                f"- {citation.chunk_id} ({citation.relative_path}:{citation.start_line}-{citation.end_line})"
            )


@app.command("context")
def context_command(
    ctx: typer.Context,
    query: str = typer.Argument(...),
    limit: int = typer.Option(5, min=1, max=20),
    max_chars: int = typer.Option(1500, min=50, max=20000),
    match_mode: str = typer.Option(
        "and",
        "--match",
        help="How FTS combines query terms: and (all) or or (any).",
    ),
    candidate_pool: int | None = typer.Option(
        None,
        "--candidate-pool",
        min=5,
        max=200,
        help="Raw hits to score before diversification (default: max(limit*6, 32)).",
    ),
    max_per_document: int = typer.Option(
        2,
        "--max-per-document",
        min=1,
        max=20,
        help="At most this many chunks per document in the final ranked list.",
    ),
) -> None:
    store = _store(ctx)
    try:
        context_pack = build_query_context(
            query=query,
            store=store,
            limit=limit,
            max_chars=max_chars,
            match_mode=match_mode,
            candidate_pool=candidate_pool,
            max_chunks_per_document=max_per_document,
        )
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"Query: {context_pack.query}")
    typer.echo(
        f"Context budget: {context_pack.used_chars}/{context_pack.max_chars} chars "
        f"(~{context_pack.estimated_input_tokens} est. tokens)"
    )
    typer.echo(
        f"Selected chunks: {len(context_pack.chunk_ids)}, topics: {len(context_pack.topic_ids)}, "
        f"claims: {len(context_pack.claim_ids)}"
    )

    if context_pack.snippets:
        typer.echo("")
        typer.echo("Context snippets:")
        for snippet in context_pack.snippets:
            preview = " ".join(snippet.text.split())
            typer.echo(
                f"- {snippet.chunk_id} ({snippet.relative_path}:{snippet.start_line}-{snippet.end_line}) score={snippet.score:.3f}"
            )
            typer.echo(f"  {preview}")


@app.command("retrieve")
def retrieve_command(
    ctx: typer.Context,
    query: str = typer.Argument(...),
    limit: int = typer.Option(5, min=1, max=20),
    match_mode: str = typer.Option(
        "and",
        "--match",
        help="How FTS combines query terms: and (all) or or (any).",
    ),
    candidate_pool: int | None = typer.Option(
        None,
        "--candidate-pool",
        min=5,
        max=200,
        help="Raw hits to fetch from FTS before diversification (default: max(limit*6, 32)).",
    ),
    max_per_document: int = typer.Option(
        2,
        "--max-per-document",
        min=1,
        max=20,
        help="At most this many chunks per document in the final ranked list.",
    ),
) -> None:
    store = _store(ctx)
    try:
        evidence_pack = retrieve_evidence(
            query=query,
            store=store,
            limit=limit,
            match_mode=match_mode,
            candidate_pool=candidate_pool,
            max_chunks_per_document=max_per_document,
        )
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"Query: {evidence_pack.query}")
    typer.echo(
        f"Match: {evidence_pack.match_mode}, ranked: {evidence_pack.ranking_strategy}, "
        f"candidates: {evidence_pack.candidate_hits_fetched}, max/doc: {evidence_pack.max_chunks_per_document}"
    )
    typer.echo(f"Chunks: {len(evidence_pack.chunk_ids)}")
    typer.echo(f"Topics: {len(evidence_pack.topic_ids)}")
    typer.echo(f"Claims: {len(evidence_pack.claim_ids)}")

    if evidence_pack.hits:
        typer.echo("")
        typer.echo("Evidence hits:")
        for hit in evidence_pack.hits:
            snippet = " ".join(hit.text.split())[:160]
            typer.echo(
                f"- {hit.chunk_id} ({hit.relative_path}:{hit.start_line}-{hit.end_line}) score={hit.score:.3f}"
            )
            typer.echo(f"  {snippet}")


@inspect_app.command("workspace")
def inspect_workspace_command(ctx: typer.Context) -> None:
    store = _store(ctx)
    inspection = inspect_workspace(store=store)

    if len(inspection.source_ids) > 1:
        typer.echo(f"Sources ({len(inspection.source_ids)}): {', '.join(inspection.source_ids)}")
    elif inspection.source_ids:
        typer.echo(f"Source: {inspection.source_ids[0]}")
    else:
        typer.echo(f"Source: {inspection.source_id}")
    typer.echo(
        f"Documents: {inspection.document_count}, chunks: {inspection.chunk_count}, "
        f"topics: {inspection.topic_count}"
    )
    typer.echo(
        f"Claims: {inspection.claim_count}, relations: {inspection.relation_count}, "
        f"themes: {inspection.theme_count}"
    )
    typer.echo(f"State dir: {inspection.state_dir}")
    typer.echo(f"Compiled dir: {inspection.compiled_dir}")
    typer.echo(f"Indexes dir: {inspection.indexes_dir}")

    try:
        evidence_pack = store.load_last_evidence_pack()
    except FileNotFoundError:
        return

    typer.echo("")
    typer.echo(
        f"Last evidence pack: query={evidence_pack.query!r}, chunks={len(evidence_pack.chunk_ids)}"
    )
    try:
        context_pack = store.load_last_context_pack()
    except FileNotFoundError:
        return
    except ValidationError:
        typer.echo(
            "Last context pack on disk is unreadable or outdated; run `context \"<query>\"` to refresh it."
        )
        return

    typer.echo(
        f"Last context pack: query={context_pack.query!r}, snippets={len(context_pack.snippets)}, "
        f"used_chars={context_pack.used_chars}"
    )


@inspect_app.command("chunk")
def inspect_chunk_command(ctx: typer.Context, chunk_id: str = typer.Argument(...)) -> None:
    store = _store(ctx)
    try:
        inspection = inspect_chunk(chunk_id=chunk_id, store=store)
    except KeyError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    chunk = inspection.chunk
    typer.echo(f"Chunk: {chunk.chunk_id}")
    typer.echo(
        f"Source: {chunk.provenance.relative_path}:{chunk.provenance.start_line}-{chunk.provenance.end_line}"
    )
    typer.echo("")
    typer.echo(chunk.text)


@inspect_app.command("topic")
def inspect_topic_command(ctx: typer.Context, topic_id: str = typer.Argument(...)) -> None:
    store = _store(ctx)
    try:
        inspection = inspect_topic(topic_id=topic_id, store=store)
    except KeyError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    topic = inspection.topic
    typer.echo(f"Topic: {topic.title} ({topic.topic_id})")
    typer.echo(f"Document: {topic.document_id}")
    typer.echo(f"Summary: {topic.summary}")
    typer.echo("")
    typer.echo(f"Supporting chunks: {len(topic.supporting_chunk_ids)}")
    typer.echo(f"Claims: {len(inspection.claims)}")
    typer.echo(f"Relations: {len(inspection.relations)}")


@app.command("trace")
def trace_command(
    ctx: typer.Context,
    run: str | None = typer.Option(
        None,
        "--run",
        help="Trace a past `ask` run by id (from `runs`); default: last-answer.json.",
    ),
) -> None:
    store = _store(ctx)
    try:
        trace = trace_ask_run(store=store, run_id=run) if run else trace_last_answer(store=store)
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error
    except (KeyError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error

    typer.echo(f"Query: {trace.answer.query}")
    typer.echo(f"Answer: {trace.answer.answer_text}")
    typer.echo("")
    typer.echo("Evidence:")
    for chunk in trace.cited_chunks:
        typer.echo(
            f"- {chunk.chunk_id} ({chunk.provenance.relative_path}:{chunk.provenance.start_line}-{chunk.provenance.end_line})"
        )
        typer.echo(f"  {chunk.text}")


@app.command("runs")
def runs_command(ctx: typer.Context, limit: int = typer.Option(10, min=1, max=100)) -> None:
    store = _store(ctx)
    runs = list_query_runs(store=store, limit=limit)

    if not runs:
        typer.echo("No query runs recorded yet.")
        return

    for run in runs:
        line = (
            f"{run.run_id} | {run.command} | query={run.query!r} | hits={run.hit_count} | chunks={run.chunk_count}"
        )
        if run.topic_count or run.claim_count:
            line += f" | topics={run.topic_count} | claims={run.claim_count}"
        typer.echo(line)
        if run.context_chars is not None:
            typer.echo(f"  context_chars={run.context_chars}")
        if run.answer_preview:
            typer.echo(f"  answer={run.answer_preview}")


def main() -> None:
    app()
