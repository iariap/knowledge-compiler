from hashlib import sha256
from pathlib import Path

from knowledge_compiler.ingestion.html_text import html_to_plain_text
from knowledge_compiler.schemas import Document


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def read_normalized_body(path: Path) -> str:
    raw_text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        return normalize_text(html_to_plain_text(raw_text))
    return normalize_text(raw_text)


def build_document(*, source_id: str, root: Path, path: Path) -> tuple[Document, str]:
    normalized_text = read_normalized_body(path)
    relative_path = path.relative_to(root).as_posix()
    content_hash = sha256(normalized_text.encode("utf-8")).hexdigest()
    title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name

    document = Document(
        document_id=f"doc-{content_hash[:16]}",
        source_id=source_id,
        relative_path=relative_path,
        absolute_path=str(path.resolve()),
        title=title,
        content_hash=content_hash,
    )
    return document, normalized_text
