"""
VeriHire v2 - Evaluation Metrics (Milestone 4)
Standard information retrieval metrics: NDCG@10, Precision@10, and Mean Reciprocal Rank (MRR).
"""

import math
from typing import Dict, List, Sequence


def compute_dcg(relevances: Sequence[float | int], k: int = 10) -> float:
    """
    Computes Discounted Cumulative Gain at rank k using standard binary log discount:
    DCG@K = sum_{i=1}^K (2^{rel_i} - 1) / log2(i + 1)
    """
    dcg = 0.0
    for idx, rel in enumerate(relevances[:k]):
        gain = (2.0 ** float(rel)) - 1.0
        discount = math.log2(idx + 2.0)  # idx 0 -> log2(2) = 1.0
        dcg += gain / discount
    return dcg


def compute_ndcg(
    ranked_candidate_ids: List[str],
    ground_truth_relevance: Dict[str, int],
    k: int = 10,
) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank k (NDCG@K).
    Returns 0.0 to 1.0. If all ground truth items are 0, returns 1.0.
    """
    actual_relevances = [
        ground_truth_relevance.get(cid, 0)
        for cid in ranked_candidate_ids[:k]
    ]
    actual_dcg = compute_dcg(actual_relevances, k=k)

    # Ideal ranking is all known candidates sorted by relevance descending
    ideal_relevances = sorted(list(ground_truth_relevance.values()), reverse=True)[:k]
    ideal_dcg = compute_dcg(ideal_relevances, k=k)

    if ideal_dcg <= 0.0:
        return 1.0 if actual_dcg <= 0.0 else 0.0

    return min(1.0, max(0.0, actual_dcg / ideal_dcg))


def compute_precision_at_k(
    ranked_candidate_ids: List[str],
    ground_truth_relevance: Dict[str, int],
    k: int = 10,
    min_relevance: int = 2,
) -> float:
    """
    Computes Precision@K: fraction of top K candidates that have relevance >= min_relevance.
    """
    if k <= 0:
        return 0.0
    top_k = ranked_candidate_ids[:k]
    if not top_k:
        return 0.0

    relevant_count = sum(
        1 for cid in top_k
        if ground_truth_relevance.get(cid, 0) >= min_relevance
    )
    return relevant_count / float(len(top_k))


def compute_mrr(
    ranked_candidate_ids: List[str],
    ground_truth_relevance: Dict[str, int],
    min_relevance: int = 2,
) -> float:
    """
    Computes Mean Reciprocal Rank (MRR): 1 / rank of first relevant candidate.
    """
    for idx, cid in enumerate(ranked_candidate_ids):
        if ground_truth_relevance.get(cid, 0) >= min_relevance:
            return 1.0 / (idx + 1.0)
    return 0.0
