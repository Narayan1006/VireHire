"""
VeriHire AI - Layer 1: RAG Semantic Filter

Orchestrates the full Layer 1 pipeline:
  1. Ingestion:  CSV -> parse -> chunk -> embed -> ChromaDB
  2. Retrieval:  JD embedding -> ChromaDB query -> score aggregation -> top-K

Score aggregation uses weighted average per candidate:
    final_score = 0.7 * max_chunk_score + 0.3 * avg_chunk_score

This reduces 9,544 candidates down to ~200 for Layer 2.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.config import Settings, get_settings
from app.embeddings.chunker import TextChunker
from app.embeddings.embedder import Embedder
from app.models.candidate import CandidateInput
from app.models.ranking import (
    CandidateMatch,
    ChromaDBDocument,
    ChromaDBMetadata,
    ParsedResume,
)
from app.parsers.csv_parser import load_csv, parse_dataframe
from app.parsers.resume_parser import ResumeParser
from app.storage.vector_store import VectorStore
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Layer1RAGFilter:
    """
    Layer 1: RAG Semantic Filter.

    Ingests candidate resumes into ChromaDB and retrieves the top-K
    most semantically similar candidates for a given job description.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.parser = ResumeParser()
        self.chunker = TextChunker()
        self.embedder = Embedder(
            model_name=self.settings.embedding_model_name,
            batch_size=self.settings.embedding_batch_size,
        )
        self.vector_store = VectorStore(
            persist_path=self.settings.chromadb_path,
            collection_name=self.settings.chromadb_collection_name,
        )

        # Cache parsed candidates for use in retrieval
        self._parsed_cache: Dict[str, ParsedResume] = {}
        self._candidate_cache: Dict[str, CandidateInput] = {}

    # ── Ingestion ─────────────────────────────────────────────────

    def ingest_candidates(
        self,
        csv_path: Optional[str] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> int:
        """
        Orchestrate full ingestion: CSV -> parse -> chunk -> embed -> store.

        Args:
            csv_path: Path to CSV on disk (local dev / default dataset).
            df: In-memory DataFrame (production uploads — no disk).

        Returns:
            Number of candidates successfully ingested.
        """
        t_start = time.time()
        if df is not None:
            logger.info("Layer 1 ingestion started: in-memory dataframe")
            candidates, total_rows = parse_dataframe(df)
        elif csv_path:
            logger.info("Layer 1 ingestion started: %s", csv_path)
            candidates, total_rows = load_csv(csv_path)
        else:
            raise ValueError("Either csv_path or df must be provided")

        if not candidates:
            logger.error("No valid candidates found in CSV")
            return 0

        logger.info(
            "Loaded %d valid candidates from %d rows",
            len(candidates),
            total_rows,
        )

        # Step 2: Create fresh collection
        self.vector_store.create_collection()

        # Step 3: Parse, chunk, embed, and collect documents
        all_documents: List[ChromaDBDocument] = []
        all_texts: List[str] = []
        text_to_doc_info: List[Tuple[CandidateInput, ParsedResume, int, str]] = []

        for candidate in candidates:
            parsed = self.parser.parse_candidate(candidate)
            chunks = self.chunker.chunk_resume(parsed)

            # Cache for later retrieval
            self._parsed_cache[candidate.id] = parsed
            self._candidate_cache[candidate.id] = candidate

            for chunk in chunks:
                all_texts.append(chunk.text)
                text_to_doc_info.append(
                    (candidate, parsed, chunk.chunk_index, chunk.chunk_type)
                )

        logger.info(
            "Parsed %d candidates into %d chunks, generating embeddings...",
            len(candidates),
            len(all_texts),
        )

        # Step 4: Batch embed all chunks at once (much faster than one-by-one)
        all_embeddings = self.embedder.embed_batch(all_texts)

        # Step 5: Build ChromaDB documents
        for i, (candidate, parsed, chunk_idx, chunk_type) in enumerate(
            text_to_doc_info
        ):
            doc = ChromaDBDocument(
                id=f"{candidate.id}_chunk_{chunk_idx}",
                embedding=all_embeddings[i],
                document=all_texts[i],
                metadata=ChromaDBMetadata(
                    candidate_id=candidate.id,
                    name=parsed.name,
                    email=parsed.email,
                    role=parsed.role,
                    skills=",".join(parsed.skills),
                    chunk_index=chunk_idx,
                    chunk_type=chunk_type,
                    matched_score=candidate.matched_score,
                ),
            )
            all_documents.append(doc)

        # Step 6: Batch insert into ChromaDB
        self.vector_store.add_candidates(all_documents)

        elapsed = time.time() - t_start
        doc_count = self.vector_store.count()
        logger.info(
            "Layer 1 ingestion complete: %d candidates, %d documents, %.2fs",
            len(candidates),
            doc_count,
            elapsed,
        )

        return len(candidates)

    # ── Retrieval ─────────────────────────────────────────────────

    def retrieve_top_candidates(
        self,
        job_description: str,
        top_k: int = 200,
        groq_api_key: str = "",
        groq_model: str = "llama-3.3-70b-versatile",
    ) -> List[CandidateMatch]:
        """
        Retrieve the top-K candidates using cosine similarity + optional LLM filter.

        Algorithm:
            1. Embed the job description
            2. Query ChromaDB for top_k * 2.5 chunks (fetch 500 for top_k=200)
            3. Aggregate scores by candidate_id (weighted average)
            4. If Groq API key provided: LLM filter batches of 50 → select best
            5. Return top_k CandidateMatch objects
        """
        t_start = time.time()
        # Fetch more candidates when LLM filter is available
        fetch_multiplier = 2.5 if groq_api_key else 1.0
        fetch_top_k = int(top_k * fetch_multiplier)

        logger.info(
            "Layer 1 retrieval started (top_k=%d, fetch=%d, JD length=%d chars, llm=%s)",
            top_k,
            fetch_top_k,
            len(job_description),
            "enabled" if groq_api_key else "disabled",
        )

        # Step 1: Embed the job description
        jd_embedding = self.embedder.embed_text(job_description)

        # Step 2: Query ChromaDB for chunks
        query_top_k = min(fetch_top_k * 5, self.vector_store.count())
        results = self.vector_store.query(jd_embedding, top_k=query_top_k)

        if not results:
            logger.warning("No results returned from ChromaDB")
            return []

        # Step 3: Aggregate scores by candidate_id
        candidate_scores: Dict[str, List[float]] = defaultdict(list)
        candidate_metadata: Dict[str, dict] = {}

        for result in results:
            cid = result.metadata.get("candidate_id", "")
            if not cid:
                continue
            candidate_scores[cid].append(result.similarity)
            if cid not in candidate_metadata:
                candidate_metadata[cid] = result.metadata

        # Calculate weighted score per candidate
        scored: List[Tuple[str, float]] = []
        for cid, scores in candidate_scores.items():
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            final_score = 0.7 * max_score + 0.3 * avg_score
            final_score = max(0.0, min(1.0, final_score))
            scored.append((cid, final_score))

        scored.sort(key=lambda x: (-x[1], x[0]))

        # Step 4: LLM filter (if API key available)
        if groq_api_key and len(scored) > top_k:
            cosine_pool = scored[:fetch_top_k]
            llm_selected = self._llm_filter(
                cosine_pool, job_description, top_k, groq_api_key, groq_model,
            )
            # Rebuild scored using LLM selection order, backfill from cosine
            llm_set = set(llm_selected)
            filtered = [(cid, sc) for cid, sc in cosine_pool if cid in llm_set]
            # Backfill if LLM returned fewer than top_k
            if len(filtered) < top_k:
                remaining = [(c, s) for c, s in cosine_pool if c not in llm_set]
                filtered.extend(remaining[: top_k - len(filtered)])
            scored = filtered[:top_k]
        else:
            scored = scored[:top_k]

        # Step 5: Build CandidateMatch objects
        matches: List[CandidateMatch] = []
        for cid, score in scored:
            meta = candidate_metadata.get(cid, {})
            parsed = self._parsed_cache.get(cid)
            candidate = self._candidate_cache.get(cid)

            match = CandidateMatch(
                candidate_id=cid,
                name=meta.get("name", parsed.name if parsed else ""),
                email=meta.get("email", parsed.email if parsed else ""),
                role=meta.get("role", parsed.role if parsed else ""),
                skills=parsed.skills if parsed else [],
                online_links=candidate.online_links if candidate else "",
                matched_score=float(meta.get("matched_score", 0.0)),
                similarity_score=score,
                timeline=parsed.timeline if parsed else [],
            )
            matches.append(match)

        elapsed = time.time() - t_start
        logger.info(
            "Layer 1 retrieval complete: %d candidates returned (from %d unique) in %.2fs",
            len(matches),
            len(candidate_scores),
            elapsed,
        )

        return matches

    # ── LLM Filter ────────────────────────────────────────────────

    def _llm_filter(
        self,
        cosine_pool: List[Tuple[str, float]],
        job_description: str,
        target_count: int,
        groq_api_key: str,
        groq_model: str,
    ) -> List[str]:
        """
        Use Groq LLM to filter candidates in batches of 50.

        Falls back to returning all IDs if LLM is unavailable.
        """
        from app.integrations.groq_client import GroqClient

        try:
            client = GroqClient(
                api_key=groq_api_key,
                model=groq_model,
                max_tokens=1000,
            )
        except Exception as e:
            logger.warning("Could not create GroqClient for L1 filter: %s", e)
            return [cid for cid, _ in cosine_pool[:target_count]]

        BATCH_SIZE = 50
        all_selected: List[str] = []

        for i in range(0, len(cosine_pool), BATCH_SIZE):
            batch = cosine_pool[i : i + BATCH_SIZE]
            batch_data = []
            for cid, score in batch:
                parsed = self._parsed_cache.get(cid)
                summary = parsed.text[:300] if parsed else ""
                batch_data.append({
                    "id": cid,
                    "name": parsed.name if parsed else cid,
                    "role": parsed.role if parsed else "",
                    "summary": summary,
                })

            selected = client.filter_candidates_batch(job_description, batch_data)
            all_selected.extend(selected)

            logger.info(
                "LLM filter batch %d: %d/%d selected",
                i // BATCH_SIZE + 1,
                len(selected),
                len(batch),
            )

        logger.info(
            "LLM filter complete: %d selected from %d total",
            len(all_selected),
            len(cosine_pool),
        )

        return all_selected

