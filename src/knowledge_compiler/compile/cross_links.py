"""Cross-topic relations from lexical overlap (compile-time, no embeddings)."""

from knowledge_compiler.retrieval.query_tokens import lexical_token_set
from knowledge_compiler.schemas import Relation, TopicRecord


def lexical_cross_topic_relations(
    records: list[TopicRecord],
    *,
    min_jaccard: float = 0.12,
    max_edges_per_topic: int = 8,
) -> list[Relation]:
    """Pair topics when title+summary token sets overlap enough (Jaccard)."""
    bags = {topic.topic_id: lexical_token_set(f"{topic.title} {topic.summary}") for topic in records}
    topic_ids = [topic.topic_id for topic in records]
    scored: list[tuple[str, str, float]] = []
    for i, left in enumerate(topic_ids):
        for right in topic_ids[i + 1 :]:
            a, b = bags[left], bags[right]
            if len(a) < 2 or len(b) < 2:
                continue
            inter = len(a & b)
            union = len(a | b)
            if union == 0:
                continue
            jaccard = inter / union
            if jaccard >= min_jaccard:
                scored.append((left, right, jaccard))

    scored.sort(key=lambda item: item[2], reverse=True)
    degree: dict[str, int] = {}
    relations: list[Relation] = []
    for left, right, _j in scored:
        if degree.get(left, 0) >= max_edges_per_topic or degree.get(right, 0) >= max_edges_per_topic:
            continue
        first, second = sorted((left, right))
        relation_id = f"xref-{first}-to-{second}"
        relations.append(
            Relation(
                relation_id=relation_id,
                subject=first,
                predicate="lexically_related_to",
                object=second,
                supporting_claim_ids=(),
            )
        )
        degree[left] = degree.get(left, 0) + 1
        degree[right] = degree.get(right, 0) + 1

    return relations
