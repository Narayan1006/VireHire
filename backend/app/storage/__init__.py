"""
VeriHire AI - Shared Store Singleton

Provides a single CandidateStore instance across all API routes.
"""

from app.storage.candidate_store_pg import CandidateStorePG

_store_instance = None


def get_store() -> CandidateStorePG:
    """Get the shared CandidateStore singleton (PostgreSQL)."""
    global _store_instance
    if _store_instance is None:
        _store_instance = CandidateStorePG()
    return _store_instance
