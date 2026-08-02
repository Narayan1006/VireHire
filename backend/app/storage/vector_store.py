"""
VeriHire AI - ChromaDB Vector Store

Wraps ChromaDB for persistent vector storage of candidate resume
embeddings.  Supports collection lifecycle, batch insertion with
metadata, cosine-similarity queries, and collection deletion for
re-ingestion.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import chromadb

from app.models.ranking import ChromaDBDocument
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueryResult:
    """A single result from a ChromaDB similarity query."""

    document_id: str
    document: str
    metadata: Dict
    distance: float  # Cosine distance (lower = more similar)
    similarity: float  # Cosine similarity (1 - distance)


class VectorStore:
    """
    ChromaDB wrapper for candidate vector storage and retrieval.

    Uses persistent storage so collections survive restarts.
    """

    def __init__(
        self,
        persist_path: str = "./data/chroma_db",
        collection_name: str = "candidates",
    ):
        self.persist_path = persist_path
        self.collection_name = collection_name
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None

    @property
    def client(self) -> chromadb.ClientAPI:
        """Lazy-initialise the ChromaDB persistent client."""
        if self._client is None:
            logger.info(
                "Initialising ChromaDB client (path=%s)", self.persist_path
            )
            self._client = chromadb.PersistentClient(path=self.persist_path)
        return self._client

    @property
    def collection(self):
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "Collection '%s' ready (%d documents)",
                self.collection_name,
                self._collection.count(),
            )
        return self._collection

    # ── Collection Lifecycle ──────────────────────────────────────

    def create_collection(self) -> None:
        """
        Create (or reset) the candidates collection.

        If the collection already exists it is deleted first to
        support clean re-ingestion.
        """
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Deleted existing collection '%s'", self.collection_name)
        except Exception:
            pass  # Collection didn't exist

        self._collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Created fresh collection '%s'", self.collection_name)

    def delete_collection(self) -> None:
        """Delete the collection entirely."""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("Deleted collection '%s'", self.collection_name)
        except Exception as e:
            logger.warning(
                "Failed to delete collection '%s': %s",
                self.collection_name,
                str(e),
            )

    # ── Insertion ─────────────────────────────────────────────────

    def add_candidates(self, documents: List[ChromaDBDocument]) -> None:
        """
        Batch-insert candidate documents into ChromaDB.

        Args:
            documents: List of ChromaDBDocument objects with embeddings
                       and metadata.
        """
        if not documents:
            logger.warning("No documents to add")
            return

        # ChromaDB batch limit is ~5000; chunk if needed
        batch_size = 5000

        for start in range(0, len(documents), batch_size):
            batch = documents[start : start + batch_size]

            ids = [doc.id for doc in batch]
            embeddings = [doc.embedding for doc in batch]
            docs = [doc.document for doc in batch]
            metadatas = [doc.metadata.model_dump() for doc in batch]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=docs,
                metadatas=metadatas,
            )

            logger.info(
                "Inserted batch %d-%d of %d documents",
                start + 1,
                start + len(batch),
                len(documents),
            )

        logger.info(
            "Total documents in collection: %d", self.collection.count()
        )

    # ── Query ─────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 200,
    ) -> List[QueryResult]:
        """
        Query the collection with a job-description embedding.

        Uses cosine similarity. Returns up to top_k results sorted by
        decreasing similarity.

        Args:
            query_embedding: 384-dimensional embedding vector.
            top_k: Maximum number of results to return.

        Returns:
            List of QueryResult objects.
        """
        count = self.collection.count()
        if count == 0:
            logger.warning("Collection is empty, no results to return")
            return []

        # Don't request more results than available documents
        n_results = min(top_k, count)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        query_results: List[QueryResult] = []

        # ChromaDB returns lists-of-lists (one per query)
        ids = results["ids"][0] if results["ids"] else []
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            query_results.append(
                QueryResult(
                    document_id=doc_id,
                    document=doc,
                    metadata=meta,
                    distance=dist,
                    similarity=max(0.0, 1.0 - dist),  # Cosine: sim = 1 - dist
                )
            )

        logger.debug(
            "Query returned %d results (top similarity: %.4f)",
            len(query_results),
            query_results[0].similarity if query_results else 0.0,
        )

        return query_results

    # ── Utility ───────────────────────────────────────────────────

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self.collection.count()
