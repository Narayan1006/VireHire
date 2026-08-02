"""
VeriHire AI - Text Chunker

Chunks parsed resumes into 3-5 semantic sections for embedding.
Each chunk targets a specific resume section (summary, experience,
skills, education).

Chunk Types:
    1. Summary    — Name + Role + Skills + Overview     (variable)
    2. Experience — Each position with context           (variable)
    3. Skills     — All skills with profile links        (variable)
    4. Education  — All education entries                (variable)

The minimum token floor is kept low (25 tokens) because the source
data is CSV-derived (short fields), not multi-page PDFs.  Sentence-
transformers handles short inputs well — repetitive padding would
pollute the semantic signal.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

from typing import List

from app.models.ranking import ParsedResume, TextChunk
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Token estimation: ~1 token ≈ 4 characters (English avg for transformer models)
CHARS_PER_TOKEN = 4

# Chunk size limits in tokens
MIN_CHUNK_TOKENS = 25   # Floor for accepting a chunk (CSV data is terse)
MAX_CHUNK_TOKENS = 500

# Target chunk counts
MIN_CHUNKS = 3
MAX_CHUNKS = 5


def _estimate_tokens(text: str) -> int:
    """Estimate the token count of a text string."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _truncate_chunk(text: str) -> str:
    """Truncate a chunk that exceeds the maximum token threshold."""
    max_chars = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


class TextChunker:
    """Chunk parsed resumes into semantic sections for embedding."""

    def chunk_resume(self, parsed_resume: ParsedResume) -> List[TextChunk]:
        """
        Create 3-5 semantic text chunks from a parsed resume.

        Preconditions:
            - parsed_resume is non-null with text content
            - parsed_resume.candidate_id is set

        Postconditions:
            - Returns 3-5 TextChunk objects
            - Chunk indices are sequential starting from 0
            - Chunks maintain semantic coherence (no noisy repetition)
        """
        cid = parsed_resume.candidate_id
        chunks: List[TextChunk] = []

        # ── 1. Summary chunk (always created) ─────────────────────
        summary = self.create_summary_chunk(parsed_resume)
        chunks.append(summary)

        # ── 2. Experience chunks ──────────────────────────────────
        exp_chunks = self.create_experience_chunks(parsed_resume)
        chunks.extend(exp_chunks)

        # ── 3. Skills chunk ───────────────────────────────────────
        skills_chunk = self.create_skills_chunk(parsed_resume)
        if skills_chunk:
            chunks.append(skills_chunk)

        # ── 4. Education chunk ────────────────────────────────────
        edu_chunk = self.create_education_chunk(parsed_resume)
        if edu_chunk:
            chunks.append(edu_chunk)

        # ── Enforce minimum (3 chunks) ────────────────────────────
        #   If data-sparse, synthesise unique additive chunks rather
        #   than duplicating existing content.
        if len(chunks) < MIN_CHUNKS and parsed_resume.online_links:
            chunks.append(
                TextChunk(
                    candidate_id=cid,
                    chunk_index=0,
                    chunk_type="summary",
                    text=(
                        f"{parsed_resume.name} is a {parsed_resume.role} candidate. "
                        f"Online profiles: {parsed_resume.online_links}. "
                        f"Responsibilities: {parsed_resume.text[:300] if parsed_resume.text else 'Not specified'}."
                    ),
                )
            )

        while len(chunks) < MIN_CHUNKS:
            # Last resort: create a context-only chunk (no repetition)
            chunks.append(
                TextChunk(
                    candidate_id=cid,
                    chunk_index=0,
                    chunk_type="summary",
                    text=(
                        f"{parsed_resume.name}, applying for {parsed_resume.role}. "
                        f"Skills include {', '.join(parsed_resume.skills[:5]) if parsed_resume.skills else 'not specified'}. "
                        f"Score: {parsed_resume.matched_score}."
                    ),
                )
            )

        # ── Enforce maximum (5 chunks) ────────────────────────────
        if len(chunks) > MAX_CHUNKS:
            summary_chunks = [c for c in chunks if c.chunk_type == "summary"][:1]
            exp_all = [c for c in chunks if c.chunk_type == "experience"]
            skills_chunks = [c for c in chunks if c.chunk_type == "skills"][:1]
            edu_chunks = [c for c in chunks if c.chunk_type == "education"][:1]

            # Merge experience chunks if too many
            if len(exp_all) > 2:
                merged_text = "\n".join(c.text for c in exp_all)
                merged_text = _truncate_chunk(merged_text)
                exp_all = [
                    TextChunk(
                        candidate_id=cid,
                        chunk_index=0,
                        chunk_type="experience",
                        text=merged_text,
                    )
                ]

            chunks = summary_chunks + exp_all + skills_chunks + edu_chunks
            chunks = chunks[:MAX_CHUNKS]

        # ── Re-index all chunks sequentially ──────────────────────
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i

        logger.debug(
            "Chunked resume for %s: %d chunks (types: %s)",
            cid,
            len(chunks),
            [c.chunk_type for c in chunks],
        )

        return chunks

    # ── Chunk Creators ────────────────────────────────────────────

    def create_summary_chunk(self, resume: ParsedResume) -> TextChunk:
        """
        Create a summary chunk: Name + Role + Skills + Overview.

        Combines identity, skills, and the first portion of resume text
        into a single cohesive overview.
        """
        parts = [f"{resume.name}, {resume.role}."]

        if resume.skills:
            parts.append(f"Key skills: {', '.join(resume.skills[:10])}.")

        # Add resume text for richer context (first portion only)
        if resume.text:
            # Skip the first line (already have name+role) and take unique content
            lines = resume.text.split("\n")
            unique_lines = [
                ln.strip() for ln in lines[1:]
                if ln.strip() and not ln.strip().startswith(resume.name)
            ]
            if unique_lines:
                parts.append(" ".join(unique_lines[:4]))

        text = "\n".join(parts)
        text = _truncate_chunk(text)

        return TextChunk(
            candidate_id=resume.candidate_id,
            chunk_index=0,
            chunk_type="summary",
            text=text,
        )

    def create_experience_chunks(self, resume: ParsedResume) -> List[TextChunk]:
        """
        Create experience chunks: one per position (max 3).

        Each chunk places the position in context of the candidate's
        role and skill set without duplicating other chunks.
        """
        exp_entries = [t for t in resume.timeline if t.type == "experience"]
        if not exp_entries:
            return []

        chunks: List[TextChunk] = []
        for entry in exp_entries[:3]:
            parts = [
                f"{resume.name} worked as {entry.title} at {entry.organization}.",
            ]
            if entry.period:
                parts.append(f"Duration: {entry.period}.")
            if entry.description:
                parts.append(entry.description)
            parts.append(f"Applying for: {resume.role}.")
            if resume.skills:
                parts.append(f"Relevant skills: {', '.join(resume.skills[:6])}.")

            text = " ".join(parts)
            text = _truncate_chunk(text)

            chunks.append(
                TextChunk(
                    candidate_id=resume.candidate_id,
                    chunk_index=0,
                    chunk_type="experience",
                    text=text,
                )
            )

        return chunks

    def create_skills_chunk(self, resume: ParsedResume) -> TextChunk | None:
        """
        Create a skills chunk: all skills with professional context.

        Differs from the summary chunk by focusing exclusively on
        technical competencies and profile links.
        """
        if not resume.skills:
            return None

        parts = [
            f"Technical competencies of {resume.name} ({resume.role}):",
            f"{', '.join(resume.skills)}.",
        ]
        if resume.online_links:
            parts.append(f"Verified via: {resume.online_links}.")

        text = " ".join(parts)
        text = _truncate_chunk(text)

        return TextChunk(
            candidate_id=resume.candidate_id,
            chunk_index=0,
            chunk_type="skills",
            text=text,
        )

    def create_education_chunk(self, resume: ParsedResume) -> TextChunk | None:
        """
        Create an education chunk: all education entries.

        Returns None if no education entries are available.
        """
        edu_entries = [t for t in resume.timeline if t.type == "education"]
        if not edu_entries:
            return None

        parts = [f"Education background for {resume.name} ({resume.role}):"]
        for entry in edu_entries:
            line = f"{entry.title} at {entry.organization}"
            if entry.period:
                line += f", {entry.period}"
            parts.append(line + ".")

        text = " ".join(parts)
        text = _truncate_chunk(text)

        return TextChunk(
            candidate_id=resume.candidate_id,
            chunk_index=0,
            chunk_type="education",
            text=text,
        )
