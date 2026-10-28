"""
VeriHire v2 - Hybrid Retrieval Service (Vector Search + Full-Text Search with RRF)
Implements Reciprocal Rank Fusion to merge semantic embeddings and BM25/FTS ranks.
Uses distinct keyword extraction (top 40, length >= 3, stopwords removed, sanitized to [a-z0-9+#.-])
and a safely parameterized OR query for the text arm to handle long job descriptions.
Supports both PostgreSQL (pgvector + tsvector) and SQLite (in-memory test fallback).
"""

import collections
from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Sequence, Tuple
import uuid

import numpy as np
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Candidate, Ranking
from app.services.embedding import compute_query_embedding

RRF_K_DEFAULT = 60
TOP_K_DEFAULT = 200

# Standard English stopwords to filter out non-informative words from job descriptions
ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves", "will", "shall", "can", "may", "might", "must", "also", "including", "within",
    "looking", "seeking", "join", "team", "role", "work", "experience", "years", "candidate",
    "required", "preferred", "responsibilities", "qualifications", "skills", "ability", "strong",
    "knowledge", "understanding", "degree", "plus", "bonus", "opportunity", "company", "position"
}

TOKEN_PATTERN = re.compile(r"[a-z0-9+#.-]+")


def extract_query_keywords(text_input: str, max_keywords: int = 40) -> List[str]:
    """
    Extracts distinct keywords from the job description:
    - Lowercase
    - Sanitized to [a-z0-9+#.-] tokens
    - Stopwords removed
    - Length >= 3
    - Top 40 by frequency
    """
    raw_tokens = TOKEN_PATTERN.findall(text_input.lower())
    filtered_tokens = []
    for raw in raw_tokens:
        token = raw.strip(".-")
        if len(token) >= 3 and token not in ENGLISH_STOPWORDS:
            filtered_tokens.append(token)

    counts = collections.Counter(filtered_tokens)
    return [token for token, _ in counts.most_common(max_keywords)]


@dataclass
class ScoredCandidate:
    candidate_id: uuid.UUID
    rank: int
    retrieval_score: float
    vector_rank: Optional[int] = None
    fts_rank: Optional[int] = None


def compute_cosine_similarity(vec_a: Sequence, vec_b: Sequence) -> float:
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _retrieve_vector_postgres(
    job_id: uuid.UUID,
    query_vector: List[float],
    limit: int,
    db: Session,
) -> List[uuid.UUID]:
    """Retrieves candidate IDs ordered by pgvector cosine distance on PostgreSQL."""
    stmt = (
        sa.select(Candidate.id)
        .where(Candidate.job_id == job_id, Candidate.embedding.isnot(None))
        .order_by(Candidate.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    return [row[0] for row in db.execute(stmt).fetchall()]


def _retrieve_fts_postgres(
    job_id: uuid.UUID,
    query_text: str,
    limit: int,
    db: Session,
) -> List[uuid.UUID]:
    """
    Retrieves candidate IDs ordered by ts_rank_cd on PostgreSQL using a safe,
    parameterized OR query built from top extracted keywords.
    """
    keywords = extract_query_keywords(query_text, max_keywords=40)
    if not keywords:
        return []

    # Join sanitized tokens with ' OR ' for websearch_to_tsquery
    or_query = " OR ".join(keywords)

    sql = text("""
        SELECT id
        FROM candidates
        WHERE job_id = :job_id
          AND search_tsv @@ websearch_to_tsquery('english', :or_query)
        ORDER BY ts_rank_cd(search_tsv, websearch_to_tsquery('english', :or_query)) DESC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"job_id": job_id, "or_query": or_query, "limit": limit}).fetchall()
    return [r[0] for r in rows]


def _retrieve_sqlite_fallback(
    job_id: uuid.UUID,
    query_text: str,
    query_vector: List[float],
    limit: int,
    db: Session,
) -> Tuple[List[uuid.UUID], List[uuid.UUID]]:
    """In-memory cosine similarity and keyword match fallback for SQLite unit tests."""
    candidates = (
        db.execute(sa.select(Candidate).where(Candidate.job_id == job_id)).scalars().all()
    )

    # 1. Vector similarity in Python
    scored_vec = []
    for c in candidates:
        if c.embedding:
            sim = compute_cosine_similarity(query_vector, c.embedding)
            scored_vec.append((c.id, sim))
    scored_vec.sort(key=lambda x: x[1], reverse=True)
    vector_ids = [cid for cid, _ in scored_vec[:limit]]

    # 2. Keyword match using extracted keywords
    keywords = set(extract_query_keywords(query_text, max_keywords=40))
    scored_text = []
    for c in candidates:
        full_text = f"{c.name} {c.resume_text}".lower()
        matches = sum(1 for kw in keywords if kw in full_text)
        if matches > 0:
            scored_text.append((c.id, matches))
    scored_text.sort(key=lambda x: x[1], reverse=True)
    fts_ids = [cid for cid, _ in scored_text[:limit]]

    return vector_ids, fts_ids


def reciprocal_rank_fusion(
    vector_ids: List[uuid.UUID],
    fts_ids: List[uuid.UUID],
    rrf_k: int = RRF_K_DEFAULT,
    top_k: int = TOP_K_DEFAULT,
) -> List[ScoredCandidate]:
    """
    Merges vector search ranks and full-text search ranks using
    Reciprocal Rank Fusion (RRF):
        RRF_score(c) = 1/(k + rank_vec) + 1/(k + rank_fts)
    Normalizes retrieval_score to a 0-1 float where rank 1 = 1.0 (or normalized by top score).
    """
    scores: Dict[uuid.UUID, float] = {}
    vec_ranks: Dict[uuid.UUID, int] = {}
    fts_ranks: Dict[uuid.UUID, int] = {}

    for rank, cid in enumerate(vector_ids, start=1):
        vec_ranks[cid] = rank
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    for rank, cid in enumerate(fts_ids, start=1):
        fts_ranks[cid] = rank
        scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

    # Sort descending by raw RRF score
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    max_score = sorted_items[0][1] if sorted_items else 1.0

    result: List[ScoredCandidate] = []
    for rank_idx, (cid, raw_score) in enumerate(sorted_items, start=1):
        # Normalize retrieval score to [0.0, 1.0]
        norm_score = round(min(1.0, raw_score / max_score), 4) if max_score > 0 else 0.0
        result.append(
            ScoredCandidate(
                candidate_id=cid,
                rank=rank_idx,
                retrieval_score=norm_score,
                vector_rank=vec_ranks.get(cid),
                fts_rank=fts_ranks.get(cid),
            )
        )

    return result


def hybrid_retrieval(
    job_id: uuid.UUID,
    query_text: str,
    db: Session,
    top_k: int = TOP_K_DEFAULT,
    rrf_k: int = RRF_K_DEFAULT,
) -> List[ScoredCandidate]:
    """
    Executes hybrid retrieval (dense vector + sparse FTS) and merges via RRF.
    """
    query_vector = compute_query_embedding(query_text)
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"

    if dialect_name == "postgresql":
        vector_ids = _retrieve_vector_postgres(
            job_id=job_id, query_vector=query_vector, limit=top_k, db=db
        )
        fts_ids = _retrieve_fts_postgres(
            job_id=job_id, query_text=query_text, limit=top_k, db=db
        )
    else:
        vector_ids, fts_ids = _retrieve_sqlite_fallback(
            job_id=job_id,
            query_text=query_text,
            query_vector=query_vector,
            limit=top_k,
            db=db,
        )

    return reciprocal_rank_fusion(
        vector_ids=vector_ids,
        fts_ids=fts_ids,
        rrf_k=rrf_k,
        top_k=top_k,
    )


def save_rankings(
    job_id: uuid.UUID,
    scored_candidates: List[ScoredCandidate],
    db: Session,
) -> List[Ranking]:
    """
    Persists rankings in the database, replacing any existing rankings for the job.
    """
    # Clear previous rankings for this job
    db.execute(sa.delete(Ranking).where(Ranking.job_id == job_id))

    new_rankings = [
        Ranking(
            job_id=job_id,
            candidate_id=sc.candidate_id,
            rank=sc.rank,
            retrieval_score=sc.retrieval_score,
        )
        for sc in scored_candidates
    ]
    db.add_all(new_rankings)
    db.commit()
    return new_rankings
