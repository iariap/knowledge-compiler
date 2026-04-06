"""Optional OpenAI-compatible chat completion for grounded answers."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from knowledge_compiler.schemas import ContextPack


def llm_synthesis_enabled() -> bool:
    return bool(os.environ.get("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "").strip())


def default_llm_model() -> str:
    raw = os.environ.get("KNOWLEDGE_COMPILER_LLM_MODEL", "gpt-4o-mini").strip()
    return raw or "gpt-4o-mini"


def default_base_url() -> str:
    raw = os.environ.get("KNOWLEDGE_COMPILER_OPENAI_BASE_URL", "https://api.openai.com").strip()
    return raw.rstrip("/") or "https://api.openai.com"


def synthesize_answer_from_context(
    *,
    query: str,
    context_pack: ContextPack,
    model: str | None = None,
) -> str:
    api_key = os.environ.get("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "").strip()
    if not api_key:
        message = "Set KNOWLEDGE_COMPILER_OPENAI_API_KEY for LLM-backed answers."
        raise OSError(message)
    use_model = (model or default_llm_model()).strip()
    base = default_base_url()
    excerpts: list[str] = []
    for snip in context_pack.snippets:
        excerpts.append(f"[{snip.chunk_id}]\n{snip.text}")
    block = "\n\n---\n\n".join(excerpts)
    system = (
        "You write short, factual answers using ONLY the numbered excerpts. "
        "Each excerpt begins with [chunk_id] on its own line. "
        "Do not invent facts or sources. If the excerpts do not support an answer, say so clearly. "
        "Do not list chunk ids in the answer body."
    )
    user = f"Question: {query}\n\nExcerpts:\n\n{block}"
    url = f"{base}/v1/chat/completions"
    body = json.dumps(
        {
            "model": use_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        message = f"LLM API HTTP {error.code}: {detail}"
        raise OSError(message) from error
    except URLError as error:
        message = f"LLM API network error: {error}"
        raise OSError(message) from error
    try:
        return str(payload["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as error:
        message = f"Unexpected LLM response shape: {payload!r}"
        raise ValueError(message) from error
