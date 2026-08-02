"""Unit tests for CSV and resume parsers."""

import os
import tempfile

import pytest

from app.parsers.csv_parser import load_csv
from app.parsers.resume_parser import ResumeParser
from app.embeddings.chunker import TextChunker


# ── CSV Parser ────────────────────────────────────────────────────


class TestCSVParser:
    """Tests for CSV parsing and validation."""

    def _write_csv(self, content: str) -> str:
        """Write CSV content to a temp file and return path."""
        fd, path = tempfile.mkstemp(suffix=".csv", dir=".")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_valid_csv(self):
        path = self._write_csv(
            "id,name,email,role,matched_score,online_links,skills,positions,responsibilities\n"
            "1,Alice,alice@test.com,Engineer,85,https://github.com/alice,Python,\"[]\",Built APIs\n"
        )
        try:
            candidates, total = load_csv(path)
            assert total == 1
            assert len(candidates) == 1
            assert candidates[0].name == "Alice"
            assert candidates[0].email == "alice@test.com"
        finally:
            os.unlink(path)

    def test_multiple_rows(self):
        path = self._write_csv(
            "id,name,email,role,matched_score,online_links,skills,positions,responsibilities\n"
            "1,Alice,a@test.com,Eng,80,,Python,\"[]\",x\n"
            "2,Bob,b@test.com,Dev,70,,Java,\"[]\",y\n"
            "3,Carol,c@test.com,SRE,60,,Go,\"[]\",z\n"
        )
        try:
            candidates, total = load_csv(path)
            assert total == 3
            assert len(candidates) == 3
        finally:
            os.unlink(path)

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_csv("/nonexistent/file.csv")

    def test_empty_csv(self):
        path = self._write_csv(
            "id,name,email,role,matched_score,online_links,skills,positions,responsibilities\n"
        )
        try:
            candidates, total = load_csv(path)
            assert total == 0
            assert len(candidates) == 0
        finally:
            os.unlink(path)


# ── Resume Parser ─────────────────────────────────────────────────


class TestResumeParser:
    """Tests for resume parsing and text chunking."""

    def setup_method(self):
        self.parser = ResumeParser()

    def test_parse_candidate_basic(self):
        from app.models.candidate import CandidateInput

        candidate = CandidateInput(
            id="1",
            name="Alice",
            email="alice@test.com",
            role="Engineer",
            skills="Python, React",
            responsibilities="Built APIs and dashboards",
        )
        parsed = self.parser.parse_candidate(candidate)
        assert parsed.candidate_id == "1"
        assert parsed.name == "Alice"
        assert "Python" in parsed.skills
        assert "React" in parsed.skills
        assert len(parsed.text) > 0

    def test_extract_skills_dedup(self):
        skills = self.parser.extract_skills("Python, python, PYTHON, React")
        assert len(skills) == 2

    def test_extract_skills_empty(self):
        assert self.parser.extract_skills("") == []
        assert self.parser.extract_skills(None) == []


# ── TextChunker ───────────────────────────────────────────────────


class TestTextChunker:
    """Tests for resume text chunking."""

    def test_chunker_produces_chunks(self):
        from app.models.ranking import ParsedResume

        chunker = TextChunker()
        parsed = ParsedResume(
            candidate_id="c1", name="Test", email="t@t.com", role="Eng",
            skills=["Python"], online_links="", matched_score=0.5,
            text="word " * 500, timeline=[],
        )
        chunks = chunker.chunk_resume(parsed)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.candidate_id == "c1"
            assert len(chunk.text) > 0

    def test_chunker_short_text(self):
        from app.models.ranking import ParsedResume

        chunker = TextChunker()
        parsed = ParsedResume(
            candidate_id="c1", name="Test", email="t@t.com", role="Eng",
            skills=[], online_links="", matched_score=0.5,
            text="Short resume.", timeline=[],
        )
        chunks = chunker.chunk_resume(parsed)
        assert len(chunks) >= 1

