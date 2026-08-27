"""Reciprocal Rank Fusion (blueprint section 9.6): RRF(d) = sum_i 1 / (k + rank_i(d))."""

import uuid

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    *ranked_id_lists: list[uuid.UUID], k: int = DEFAULT_RRF_K
) -> list[tuple[uuid.UUID, float]]:
    """Each argument is a list of ids in descending relevance order from one
    retrieval method (vector, lexical, ...). Returns (id, fused_score) pairs
    sorted by fused score descending."""
    scores: dict[uuid.UUID, float] = {}
    for ranked_ids in ranked_id_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
