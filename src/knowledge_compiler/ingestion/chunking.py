from hashlib import sha256

from knowledge_compiler.schemas import Chunk, ChunkProvenance, Document

MAX_CHUNK_CHARS = 1_200


def chunk_document(document: Document, text: str) -> list[Chunk]:
    lines = text.split("\n")
    paragraphs: list[tuple[int, int, str]] = []

    start_line = 1
    buffer: list[str] = []
    buffer_start = 1

    for index, line in enumerate(lines, start=1):
        if line.strip():
            if not buffer:
                buffer_start = index
            buffer.append(line)
            continue

        if buffer:
            paragraphs.append((buffer_start, index - 1, "\n".join(buffer).strip()))
            buffer = []
        start_line = index + 1

    if buffer:
        paragraphs.append((buffer_start, len(lines), "\n".join(buffer).strip()))

    chunks: list[Chunk] = []
    current_lines: list[str] = []
    current_start = start_line
    current_end = start_line

    for paragraph_start, paragraph_end, paragraph_text in paragraphs:
        proposed_lines = [*current_lines, paragraph_text]
        proposed_text = "\n\n".join(proposed_lines)

        if current_lines and len(proposed_text) > MAX_CHUNK_CHARS:
            chunks.append(
                _build_chunk(
                    document=document,
                    ordinal=len(chunks),
                    text="\n\n".join(current_lines),
                    start_line=current_start,
                    end_line=current_end,
                )
            )
            current_lines = [paragraph_text]
            current_start = paragraph_start
            current_end = paragraph_end
            continue

        if not current_lines:
            current_start = paragraph_start

        current_lines.append(paragraph_text)
        current_end = paragraph_end

    if current_lines:
        chunks.append(
            _build_chunk(
                document=document,
                ordinal=len(chunks),
                text="\n\n".join(current_lines),
                start_line=current_start,
                end_line=current_end,
            )
        )

    return chunks


def _build_chunk(
    *,
    document: Document,
    ordinal: int,
    text: str,
    start_line: int,
    end_line: int,
) -> Chunk:
    text_hash = sha256(text.encode("utf-8")).hexdigest()
    return Chunk(
        chunk_id=f"{document.document_id}-chunk-{ordinal:04d}",
        document_id=document.document_id,
        ordinal=ordinal,
        text=text,
        text_hash=text_hash,
        provenance=ChunkProvenance(
            source_id=document.source_id,
            document_id=document.document_id,
            relative_path=document.relative_path,
            start_line=start_line,
            end_line=end_line,
        ),
    )
