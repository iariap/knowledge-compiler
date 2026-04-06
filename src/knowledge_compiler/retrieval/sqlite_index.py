import sqlite3
from pathlib import Path

from knowledge_compiler.retrieval.query_tokens import MatchMode, fts_match_expression
from knowledge_compiler.schemas import Chunk, SearchHit


class SqliteChunkIndex:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def rebuild(self, chunks: list[Chunk]) -> int:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute("DROP TABLE IF EXISTS chunks")
            connection.execute("DROP TABLE IF EXISTS chunks_fts")
            connection.execute(
                """
                CREATE VIRTUAL TABLE chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    document_id UNINDEXED,
                    relative_path UNINDEXED,
                    start_line UNINDEXED,
                    end_line UNINDEXED,
                    text
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO chunks_fts (
                    chunk_id,
                    document_id,
                    relative_path,
                    start_line,
                    end_line,
                    text
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.provenance.relative_path,
                        chunk.provenance.start_line,
                        chunk.provenance.end_line,
                        chunk.text,
                    )
                    for chunk in chunks
                ],
            )
            connection.commit()
        return len(chunks)

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        match_mode: MatchMode = MatchMode.AND,
    ) -> list[SearchHit]:
        match_query = fts_match_expression(query, mode=match_mode)
        if not match_query:
            return []

        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    chunk_id,
                    document_id,
                    relative_path,
                    -bm25(chunks_fts) AS score,
                    text,
                    start_line,
                    end_line
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY bm25(chunks_fts)
                LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()

        return [
            SearchHit(
                chunk_id=row[0],
                document_id=row[1],
                relative_path=row[2],
                score=float(row[3]),
                text=row[4],
                start_line=int(row[5]),
                end_line=int(row[6]),
            )
            for row in rows
        ]
