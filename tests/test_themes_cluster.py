from knowledge_compiler.compile.themes import cluster_topics_lexical
from knowledge_compiler.schemas import TopicRecord


def test_cluster_merges_lexically_similar_topics() -> None:
    topics = [
        TopicRecord(
            topic_id="t1",
            title="Python asyncio patterns",
            summary="asyncio gather and tasks for concurrent python",
            supporting_chunk_ids=("x",),
            document_id="d1",
        ),
        TopicRecord(
            topic_id="t2",
            title="More asyncio in Python",
            summary="python asyncio event loop tips",
            supporting_chunk_ids=("y",),
            document_id="d2",
        ),
        TopicRecord(
            topic_id="t3",
            title="Cooking pasta",
            summary="boil water salt olive oil",
            supporting_chunk_ids=("z",),
            document_id="d3",
        ),
    ]
    themes, mapping = cluster_topics_lexical(topics)
    assert len(themes) >= 2
    assert mapping["t1"][0] == mapping["t2"][0]
    assert mapping["t3"][0] != mapping["t1"][0]
