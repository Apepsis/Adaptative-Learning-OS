import uuid

from app.modules.retrieval.ranking import reciprocal_rank_fusion


def test_item_ranked_first_in_both_lists_wins() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    fused = reciprocal_rank_fusion([a, b, c], [a, c, b])
    assert fused[0][0] == a


def test_item_only_in_one_list_still_scores() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    fused = reciprocal_rank_fusion([a], [b])
    scores = dict(fused)
    assert scores[a] > 0
    assert scores[b] > 0


def test_scores_are_sorted_descending() -> None:
    ids = [uuid.uuid4() for _ in range(5)]
    fused = reciprocal_rank_fusion(ids, list(reversed(ids)))
    scores = [score for _, score in fused]
    assert scores == sorted(scores, reverse=True)


def test_empty_lists_produce_no_results() -> None:
    assert reciprocal_rank_fusion([], []) == []


def test_k_parameter_changes_relative_weighting() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    # a is rank 1, b is rank 2, in a single list.
    low_k = dict(reciprocal_rank_fusion([a, b], k=1))
    high_k = dict(reciprocal_rank_fusion([a, b], k=1000))
    # With small k, rank 1 dominates rank 2 much more sharply than with
    # large k, where all ranks converge toward similar scores.
    assert (low_k[a] / low_k[b]) > (high_k[a] / high_k[b])
