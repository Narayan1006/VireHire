import os
from pathlib import Path
import sys

ROOT_DIR = str(Path(__file__).resolve().parents[3])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:password@localhost:5433/verihire")
os.environ.setdefault("JWT_SECRET", "test-secret-key-that-is-at-least-32-characters-long!!")

from eval.baselines import EvaluationBaselines  # noqa: E402
from eval.dataset import CANDIDATE_POOL, EVAL_QUERIES  # noqa: E402
from eval.metrics import compute_mrr, compute_ndcg, compute_precision_at_k  # noqa: E402


def test_eval_dcg_and_ndcg_properties():
    # Ideal ranking: 3, 2, 1, 0
    gt = {"a": 3, "b": 2, "c": 1, "d": 0}
    perfect_rank = ["a", "b", "c", "d"]
    reversed_rank = ["d", "c", "b", "a"]

    ndcg_perfect = compute_ndcg(perfect_rank, gt, k=4)
    ndcg_reversed = compute_ndcg(reversed_rank, gt, k=4)

    assert ndcg_perfect == 1.0
    assert 0.0 <= ndcg_reversed < 1.0


def test_eval_precision_at_k_and_mrr():
    gt = {"c1": 3, "c2": 2, "c3": 1, "c4": 0}
    ranked = ["c1", "c3", "c2", "c4"]

    # At k=2: c1 (rel 3 >= 2) and c3 (rel 1 < 2) -> 1/2 = 0.5
    p2 = compute_precision_at_k(ranked, gt, k=2, min_relevance=2)
    assert p2 == 0.5

    # MRR: first relevant is c1 at index 0 (rank 1) -> 1/1 = 1.0
    mrr = compute_mrr(ranked, gt, min_relevance=2)
    assert mrr == 1.0

    # If first relevant is at index 1 -> 1/2 = 0.5
    mrr_second = compute_mrr(["c3", "c1", "c4"], gt, min_relevance=2)
    assert mrr_second == 0.5


def test_eval_baselines_execution():
    """Verifies that all 4 evaluation baselines execute and return candidate rankings."""
    baselines = EvaluationBaselines(CANDIDATE_POOL)
    test_query = EVAL_QUERIES[0]["description"]

    # 1. Keyword
    kw_res = baselines.run_keyword_baseline(test_query)
    assert len(kw_res) == len(CANDIDATE_POOL)
    assert isinstance(kw_res[0], str)

    # 2. Dense Embeddings
    dense_res = baselines.run_embeddings_baseline(test_query)
    assert len(dense_res) == len(CANDIDATE_POOL)
    assert 0.0 <= dense_res[0][1] <= 1.0

    # 3. Hybrid RRF
    hybrid_res = baselines.run_hybrid_rrf_baseline(test_query)
    assert len(hybrid_res) == len(CANDIDATE_POOL)
    assert 0.0 <= hybrid_res[0][1] <= 1.0

    # 4. Full Pipeline
    full_res = baselines.run_full_pipeline(test_query)
    assert len(full_res) == len(CANDIDATE_POOL)
    assert "final_score" in full_res[0]
    assert "label" in full_res[0]
    assert full_res[0]["final_score"] >= full_res[-1]["final_score"]
