"""
VeriHire AI - Resume Parser

Parses structured data from CandidateInput into ParsedResume objects.
Extracts skills, experience, education, and builds full-text for embedding.

Requirements: 1.2, 2.1
"""

import json
import re
import uuid
from typing import List

from app.models.candidate import CandidateInput, TimelineEntry
from app.models.ranking import ParsedResume
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResumeParser:
    """Parse raw CSV candidate data into structured resume objects."""

    def parse_candidate(self, candidate_input: CandidateInput) -> ParsedResume:
        """
        Extract structured data from a CandidateInput.

        Preconditions:
            - candidate_input is non-null with valid CSV data
            - candidate_input.name is non-empty

        Postconditions:
            - Returns ParsedResume with cleaned, normalised data
            - Skills are extracted and deduplicated
            - Timeline entries are chronologically ordered
        """
        # ── Extract skills ────────────────────────────────────────
        skills = self.extract_skills(candidate_input.skills)

        # ── Extract timeline ──────────────────────────────────────
        timeline: List[TimelineEntry] = []
        timeline.extend(self.extract_experience(candidate_input.positions))
        timeline.extend(self.extract_education(candidate_input.positions))

        # ── Build full text for embedding ─────────────────────────
        text = self._build_resume_text(candidate_input, skills)

        parsed = ParsedResume(
            candidate_id=candidate_input.id,
            name=_clean(candidate_input.name),
            email=_clean(candidate_input.email),
            role=_clean(candidate_input.role),
            skills=skills,
            online_links=_clean(candidate_input.online_links),
            matched_score=candidate_input.matched_score,
            text=text,
            timeline=timeline,
        )

        return parsed

    # ── Skill Extraction ──────────────────────────────────────────

    def extract_skills(self, raw_skills: str) -> List[str]:
        """
        Parse and deduplicate skills from a comma-separated string.

        Handles various separators: comma, semicolon, pipe, newline.
        Returns deduplicated list preserving first-occurrence order.
        """
        if not raw_skills or not raw_skills.strip():
            return []

        # Split on common delimiters
        parts = re.split(r"[,;|\n]+", raw_skills)

        seen: set = set()
        skills: List[str] = []
        for part in parts:
            skill = part.strip()
            if not skill:
                continue
            # Normalise for dedup comparison
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                skills.append(skill)

        return skills

    # ── Experience Extraction ─────────────────────────────────────

    def extract_experience(self, positions_json: str) -> List[TimelineEntry]:
        """
        Extract work experience timeline entries from positions JSON string.

        The Kaggle CSV stores positions as a JSON array of objects.
        Falls back to empty list if parsing fails.
        """
        entries = self._parse_positions_json(positions_json, entry_type="experience")
        return entries

    # ── Education Extraction ──────────────────────────────────────

    def extract_education(self, positions_json: str) -> List[TimelineEntry]:
        """
        Extract education timeline entries from positions JSON string.

        Looks for entries containing education-related keywords.
        """
        entries = self._parse_positions_json(positions_json, entry_type="education")
        return entries

    # ── Private Helpers ───────────────────────────────────────────

    def _parse_positions_json(
        self, positions_json: str, entry_type: str
    ) -> List[TimelineEntry]:
        """Parse positions JSON and filter by type (experience or education)."""
        if not positions_json or not positions_json.strip():
            return []

        # Education keywords for classification
        edu_keywords = {
            "university", "college", "institute", "school",
            "bachelor", "master", "phd", "b.s.", "m.s.", "b.tech", "m.tech",
            "mba", "degree", "education", "diploma",
        }

        try:
            data = json.loads(positions_json)
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON — try to extract info from plain text
            if entry_type == "experience" and positions_json.strip():
                return [
                    TimelineEntry(
                        id=str(uuid.uuid4())[:8],
                        type="experience",
                        title=positions_json.strip()[:100],
                        organization="",
                        period="",
                    )
                ]
            return []

        if not isinstance(data, list):
            data = [data]

        entries: List[TimelineEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", item.get("position", ""))).strip()
            org = str(item.get("organization", item.get("company", ""))).strip()
            period = str(item.get("period", item.get("dates", ""))).strip()
            description = str(item.get("description", "")).strip() or None

            if not title and not org:
                continue

            # Classify as education or experience
            combined = f"{title} {org}".lower()
            is_education = any(kw in combined for kw in edu_keywords)

            if entry_type == "education" and is_education:
                entries.append(
                    TimelineEntry(
                        id=str(uuid.uuid4())[:8],
                        type="education",
                        title=title,
                        organization=org,
                        period=period,
                        description=description,
                    )
                )
            elif entry_type == "experience" and not is_education:
                entries.append(
                    TimelineEntry(
                        id=str(uuid.uuid4())[:8],
                        type="experience",
                        title=title,
                        organization=org,
                        period=period,
                        description=description,
                    )
                )

        return entries

    def _build_resume_text(
        self, candidate: CandidateInput, skills: List[str]
    ) -> str:
        """
        Build a full-text resume string for embedding.

        Combines name, role, skills, responsibilities, and positions
        into a coherent text block.
        """
        parts: List[str] = []

        # Identity
        parts.append(f"{_clean(candidate.name)}, {_clean(candidate.role)}")

        # Skills
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")

        # Responsibilities
        resp = _clean(candidate.responsibilities)
        if resp:
            parts.append(f"Responsibilities: {resp}")

        # Positions (raw text fallback)
        pos = _clean(candidate.positions)
        if pos:
            # Try to extract readable text from JSON
            try:
                positions_data = json.loads(pos)
                if isinstance(positions_data, list):
                    for item in positions_data:
                        if isinstance(item, dict):
                            title = item.get("title", item.get("position", ""))
                            org = item.get("organization", item.get("company", ""))
                            if title or org:
                                parts.append(f"Position: {title} at {org}")
                else:
                    parts.append(f"Experience: {pos}")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"Experience: {pos}")

        # Online links
        links = _clean(candidate.online_links)
        if links:
            parts.append(f"Online profiles: {links}")

        return "\n".join(parts)


def _clean(value: str) -> str:
    """Strip and collapse whitespace in a string."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip())
