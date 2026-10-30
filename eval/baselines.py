"""
VeriHire v2 - Evaluation Baselines (Milestone 4)
Implements four comparative retrieval & ranking architectures:
1. Keyword / Lexical Matching (BM25 token-overlap baseline)
2. Dense Vector Embeddings Only (BAAI/bge-small-en-v1.5 cosine similarity)
3. Hybrid RRF (Lexical + Dense merged via Reciprocal Rank Fusion)
4. Full VeriHire Pipeline (Hybrid + Multi-Signal Evidence + Deterministic Confidence Weighting)
"""

from collections import Counter
import math
import re
from typing import Any, Dict, List, Tuple

from app.services.embedding import compute_embeddings
from app.services.scoring import score_candidate


def tokenize(text: str) -> List[str]:
    """Extracts alphanumeric words lowercase."""
    return re.findall(r"\b[a-zA-Z0-9_\+#\.]+\b", text.lower())


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EvaluationBaselines:
    def __init__(self, candidates: List[Dict[str, Any]]):
        self.candidates = candidates
        self.candidate_map = {c["id"]: c for c in candidates}

        # Pre-compute resume embeddings for efficiency
        texts = [f"{c['name']}\n{c['resume_text']}" for c in candidates]
        self.embeddings = compute_embeddings(texts, batch_size=16)
        self.candidate_embeddings = {
            c["id"]: emb for c, emb in zip(candidates, self.embeddings)
        }

    def run_keyword_baseline(self, query_text: str) -> List[str]:
        """
        Baseline 1: Keyword / BM25 term overlap matching.
        Ranks candidates by token frequency overlap against the query.
        """
        q_tokens = set(tokenize(query_text))
        scored = []

        for c in self.candidates:
            c_tokens = tokenize(c["resume_text"])
            token_counts = Counter(c_tokens)
            score = sum(math.log1p(token_counts[t]) for t in q_tokens if t in token_counts)
            scored.append((c["id"], score))

        # Sort descending by score
        scored.sort(key=lambda x: -x[1])
        return [cid for cid, _ in scored]

    def run_embeddings_baseline(self, query_text: str) -> List[Tuple[str, float]]:
        """
        Baseline 2: Dense semantic embeddings only.
        Ranks candidates by cosine similarity against query vector.
        """
        q_emb = compute_embeddings([query_text], batch_size=1)[0]
        scored = []

        for c in self.candidates:
            cand_emb = self.candidate_embeddings[c["id"]]
            sim = cosine_similarity(q_emb, cand_emb)
            # Map [-1, 1] cosine similarity to normalized [0, 1]
            norm_sim = min(1.0, max(0.0, (sim + 1.0) / 2.0))
            scored.append((c["id"], norm_sim))

        scored.sort(key=lambda x: -x[1])
        return scored

    def run_hybrid_rrf_baseline(self, query_text: str, k: int = 60) -> List[Tuple[str, float]]:
        """
        Baseline 3: Hybrid Retrieval using Reciprocal Rank Fusion (RRF).
        Merges lexical keyword ranks and dense vector ranks.
        """
        kw_ranked = self.run_keyword_baseline(query_text)
        dense_scored = self.run_embeddings_baseline(query_text)
        dense_ranked = [cid for cid, _ in dense_scored]

        rrf_scores: Dict[str, float] = {c["id"]: 0.0 for c in self.candidates}

        for rank_idx, cid in enumerate(kw_ranked):
            rrf_scores[cid] += 1.0 / (k + rank_idx + 1)

        for rank_idx, cid in enumerate(dense_ranked):
            rrf_scores[cid] += 1.0 / (k + rank_idx + 1)

        # Normalize RRF scores to 0-1 range
        max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0
        min_rrf = min(rrf_scores.values()) if rrf_scores else 0.0
        denom = (max_rrf - min_rrf) if max_rrf > min_rrf else 1.0

        normalized = [
            (cid, (score - min_rrf) / denom)
            for cid, score in rrf_scores.items()
        ]
        normalized.sort(key=lambda x: -x[1])
        return normalized

    def run_full_pipeline(
        self,
        query_text: str,
        settings: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Baseline 4: Full VeriHire Pipeline.
        Hybrid RRF retrieval + deterministic evidence scoring + confidence weighting.
        """
        hybrid_results = self.run_hybrid_rrf_baseline(query_text)
        final_ranked = []

        for cid, retrieval_score in hybrid_results:
            cand = self.candidate_map[cid]
            cand_evidence = cand.get("evidence", [])

            # Run deterministic scoring engine
            score_res = score_candidate(
                retrieval_score=retrieval_score,
                job_description=query_text,
                evidence_rows=cand_evidence,
                settings=settings,
            )

            final_ranked.append({
                "candidate_id": cid,
                "name": cand["name"],
                "retrieval_score": retrieval_score,
                "evidence_score": score_res["evidence_score"],
                "confidence": score_res["confidence"],
                "final_score": score_res["final_score"],
                "label": score_res["label"],
                "reasons": score_res["breakdown"].get("reasons", []),
            })

        # Sort by final_score descending, tie-break with retrieval_score
        final_ranked.sort(key=lambda x: (-x["final_score"], -x["retrieval_score"]))
        return final_ranked
