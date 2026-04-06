from knowledge_compiler.compile.cross_links import lexical_cross_topic_relations
from knowledge_compiler.schemas import TopicRecord


def test_lexical_cross_topic_relations_link_overlapping_summaries() -> None:
    alpha = TopicRecord(
        topic_id="topic-alpha",
        title="REST API caching",
        summary="HTTP cache headers and validation for REST services.",
        supporting_chunk_ids=("c1",),
        document_id="d1",
    )
    beta = TopicRecord(
        topic_id="topic-beta",
        title="HTTP performance",
        summary="Use cache headers on REST APIs to reduce load.",
        supporting_chunk_ids=("c2",),
        document_id="d2",
    )
    relations = lexical_cross_topic_relations([alpha, beta], min_jaccard=0.08, max_edges_per_topic=4)
    assert len(relations) == 1
    relation = relations[0]
    assert relation.predicate == "lexically_related_to"
    assert {relation.subject, relation.object} == {"topic-alpha", "topic-beta"}


def test_lexical_cross_topic_relations_empty_when_disjoint() -> None:
    a = TopicRecord(
        topic_id="a",
        title="Quantum chemistry",
        summary="Electron density functionals.",
        supporting_chunk_ids=("c1",),
        document_id="d1",
    )
    b = TopicRecord(
        topic_id="b",
        title="Bread baking",
        summary="Sourdough fermentation timing.",
        supporting_chunk_ids=("c2",),
        document_id="d2",
    )
    assert lexical_cross_topic_relations([a, b], min_jaccard=0.15) == []
