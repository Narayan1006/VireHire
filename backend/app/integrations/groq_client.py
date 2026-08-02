"""
VeriHire AI - Groq LLM Client

Wraps the Groq API (OpenAI-compatible) for candidate explanation generation.
Uses llama3-70b-8192 to produce 100-300 word evidence-based hiring summaries.

Features:
  - Structured prompt building with candidate evidence
  - Fallback template when API fails
  - Response parsing and word-count validation
  - Exponential backoff retry (up to 3 attempts)

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import time
from typing import Optional

import requests

from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0


class GroqClient:
    """Groq API client for LLM-generated candidate explanations."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama3-70b-8192",
        base_url: str = "https://api.groq.com/openai/v1",
        max_tokens: int = 500,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    # ── Main API ──────────────────────────────────────────────────

    def generate_explanation(self, candidate) -> str:
        """
        Generate a hiring explanation for a ScoredCandidate.

        Builds a structured prompt from candidate evidence, calls
        the Groq API, and returns a 100-300 word summary.

        Falls back to a template-based explanation on API failure.

        Args:
            candidate: ScoredCandidate with scores and evidence.

        Returns:
            Plain English explanation string (100-300 words).
        """
        system_prompt = self._build_system_prompt()
        candidate_prompt = self._build_candidate_prompt(candidate)

        try:
            response = self._chat_completion(
                system_prompt=system_prompt,
                user_prompt=candidate_prompt,
            )

            if response and len(response.split()) >= 30:
                return response

            logger.warning(
                "LLM response too short for %s, using fallback",
                candidate.name,
            )
        except Exception as e:
            logger.warning(
                "Groq API failed for %s: %s, using fallback",
                candidate.name,
                str(e),
            )

        return self._generate_fallback(candidate)

    # ── Prompt Building ───────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM."""
        return (
            "You are an expert technical recruiter analyzing candidate profiles "
            "for hiring decisions.\n\n"
            "Your task is to write a concise, evidence-based summary (100-300 words) explaining:\n"
            "1. The candidate's verified technical strengths\n"
            "2. How their skills match the role requirements\n"
            "3. Any concerns or gaps identified in verification\n"
            "4. A clear hiring recommendation\n\n"
            "Guidelines:\n"
            "- Use ONLY the provided verified data (GitHub, LeetCode, Codeforces)\n"
            "- Mention specific evidence (e.g., 'LeetCode rating of 2145', "
            "'GitHub shows 47 repos')\n"
            "- Highlight risk flags if present\n"
            "- Be objective and data-driven\n"
            "- Write in plain English for non-technical recruiters\n"
            "- End with a clear recommendation: HIRE, REVIEW, or REJECT"
        )

    def _build_candidate_prompt(self, candidate) -> str:
        """Build the candidate-specific prompt with all evidence."""
        lines = []
        lines.append(f"Candidate: {candidate.name}")
        lines.append(f"Role: {candidate.role}")
        lines.append("")

        # Scores
        lines.append("SCORES:")
        lines.append(f"- GitHub Score: {candidate.github_score}/100")
        lines.append(f"- DSA Score: {candidate.dsa_score}/100")
        lines.append(
            f"- Consistency Score: {round(candidate.consistency_score * 100)}%"
        )
        lines.append(
            f"- Semantic Match: {round(candidate.layer1_score * 100)}%"
        )
        lines.append("")

        # GitHub evidence
        gh = candidate.github_evidence
        lines.append("GITHUB EVIDENCE:")
        if gh.verified:
            lines.append(f"- Repositories: {gh.repo_count}")
            langs = ", ".join(
                f"{l.name} ({l.percentage}%)" for l in gh.languages[:5]
            )
            lines.append(f"- Languages: {langs}")
            lines.append(f"- Architecture Score: {gh.architecture_score}/100")
            lines.append(f"- AI Usage Level: {gh.ai_usage_level}")
            lines.append(f"- Last Active: {gh.last_active}")
        else:
            lines.append("- Not verified (no GitHub profile found)")
        lines.append("")

        # LeetCode evidence
        lc = candidate.leetcode_stats
        lines.append("LEETCODE EVIDENCE:")
        if lc.verified:
            lines.append(f"- Rating: {lc.rating}")
            lines.append(
                f"- Problems Solved: {lc.problems_solved} "
                f"(Easy: {lc.easy}, Medium: {lc.medium}, Hard: {lc.hard})"
            )
            lines.append(f"- Consistency: {lc.consistency}%")
        else:
            lines.append("- Not verified (no LeetCode profile found)")
        lines.append("")

        # Codeforces evidence
        cf = candidate.codeforces_stats
        lines.append("CODEFORCES EVIDENCE:")
        if cf and cf.verified:
            lines.append(f"- Rating: {cf.rating} (Max: {cf.max_rating})")
            lines.append(f"- Rank: {cf.rank}")
            lines.append(f"- Contests: {cf.contests_participated}")
        else:
            lines.append("- Not verified (no Codeforces profile found)")
        lines.append("")

        # Skill verification
        if candidate.skill_scores:
            lines.append("SKILL VERIFICATION:")
            for sc in candidate.skill_scores:
                lines.append(
                    f"- {sc.name}: claimed={sc.claimed}, verified={sc.verified}"
                )
            lines.append("")

        # Risk flags
        if candidate.risk_flags:
            lines.append("RISK FLAGS:")
            for flag in candidate.risk_flags:
                lines.append(f"- [{flag.severity.upper()}] {flag.label}: {flag.description}")
            lines.append("")

        lines.append("Write a hiring summary for this candidate.")

        return "\n".join(lines)

    # ── Fallback ──────────────────────────────────────────────────

    def _generate_fallback(self, candidate) -> str:
        """
        Generate a template-based explanation when the API fails.

        Uses candidate scores and evidence to produce a
        structured summary without LLM assistance.
        """
        name = candidate.name
        role = candidate.role
        gh_score = candidate.github_score
        dsa_score = candidate.dsa_score
        consistency = round(candidate.consistency_score * 100)

        parts = [f"{name} is being evaluated for the {role} position."]

        # GitHub summary
        gh = candidate.github_evidence
        if gh.verified:
            langs = ", ".join(l.name for l in gh.languages[:3])
            parts.append(
                f"GitHub verification shows {gh.repo_count} repositories "
                f"with primary languages: {langs}. "
                f"Architecture score: {gh.architecture_score}/100. "
                f"Last active: {gh.last_active}."
            )
        else:
            parts.append("No GitHub profile was found for verification.")

        # LeetCode summary
        lc = candidate.leetcode_stats
        if lc.verified:
            parts.append(
                f"LeetCode profile shows {lc.problems_solved} problems solved "
                f"(Easy: {lc.easy}, Medium: {lc.medium}, Hard: {lc.hard}) "
                f"with a contest rating of {lc.rating}."
            )

        # Codeforces summary
        cf = candidate.codeforces_stats
        if cf and cf.verified:
            parts.append(
                f"Codeforces profile shows a rating of {cf.rating} "
                f"(max: {cf.max_rating}), rank: {cf.rank}, "
                f"with {cf.contests_participated} contests."
            )

        # Risk flags
        if candidate.risk_flags:
            flag_text = "; ".join(
                f"{f.label} ({f.severity})" for f in candidate.risk_flags
            )
            parts.append(f"Noted concerns: {flag_text}.")

        # Scores summary
        parts.append(
            f"Overall scores: GitHub {gh_score}/100, DSA {dsa_score}/100, "
            f"Consistency {consistency}%."
        )

        # Verdict
        avg_score = (gh_score + dsa_score) / 2
        if avg_score >= 70 and consistency >= 70:
            parts.append("Recommendation: HIRE.")
        elif avg_score >= 40 or consistency >= 50:
            parts.append("Recommendation: REVIEW.")
        else:
            parts.append("Recommendation: REJECT.")

        return " ".join(parts)

    # ── Layer 1: LLM Candidate Filter ──────────────────────────────

    def filter_candidates_batch(
        self,
        job_description: str,
        candidates: list,
    ) -> list:
        """
        Ask LLM to select the most relevant candidates from a batch.

        Args:
            job_description: The JD text.
            candidates: List of dicts with {id, name, role, summary}.

        Returns:
            List of selected candidate IDs. On failure, returns all IDs.
        """
        import json as _json, re as _re

        all_ids = [c["id"] for c in candidates]

        profiles = "\n".join(
            f"ID: {c['id']} | Name: {c['name']} | Role: {c['role']} | "
            f"Summary: {c['summary'][:300]}"
            for c in candidates
        )

        system = (
            "You are a technical recruiter AI. Given a job description and "
            "candidate profiles, select the most relevant candidates.\n"
            "Return ONLY a JSON array of candidate IDs. No explanation."
        )
        user = (
            f"Job Description:\n{job_description[:2000]}\n\n"
            f"Candidates:\n{profiles}\n\n"
            f"Select the top {max(1, len(candidates) // 2)} most relevant "
            f"candidate IDs. Return JSON array only."
        )

        try:
            raw = self._chat_completion(system, user)
            if not raw:
                return all_ids

            # Parse JSON array from response
            match = _re.search(r'\[.*?\]', raw, _re.DOTALL)
            if match:
                ids = _json.loads(match.group())
                # Ensure they're strings and valid
                valid = [str(i) for i in ids if str(i) in all_ids]
                if valid:
                    return valid

            return all_ids
        except Exception as e:
            logger.warning("LLM filter failed: %s, returning all IDs", str(e))
            return all_ids

    # ── Layer 2: LLM Evidence Analysis ────────────────────────────

    def analyze_evidence_batch(
        self,
        job_description: str,
        candidates_data: list,
    ) -> list:
        """
        Ask LLM to score candidates based on their evidence data.

        Args:
            job_description: The JD text.
            candidates_data: List of dicts with {id, name, github_data, leetcode_data}.

        Returns:
            List of dicts: {id, technical_depth, role_fit, evidence_strength}.
            On failure, returns neutral scores (50) for all.
        """
        import json as _json, re as _re

        neutral = [
            {"id": c["id"], "technical_depth": 50, "role_fit": 50, "evidence_strength": 50}
            for c in candidates_data
        ]

        profiles = "\n---\n".join(
            f"ID: {c['id']}\nName: {c['name']}\n"
            f"GitHub: {c.get('github_data', 'No data')}\n"
            f"LeetCode: {c.get('leetcode_data', 'No data')}"
            for c in candidates_data
        )

        system = (
            "You are a technical assessment AI. Analyze candidate evidence "
            "and score each candidate.\n"
            "For EACH candidate, return a JSON object with:\n"
            "- id: candidate ID\n"
            "- technical_depth: 0-100 (code quality, language diversity, architecture)\n"
            "- role_fit: 0-100 (how well evidence matches the job requirements)\n"
            "- evidence_strength: 0-100 (quantity and recency of verifiable evidence)\n\n"
            "Return ONLY a JSON array of objects. No explanation."
        )
        user = (
            f"Job Description:\n{job_description[:2000]}\n\n"
            f"Candidates:\n{profiles}\n\n"
            f"Score all {len(candidates_data)} candidates. Return JSON array only."
        )

        try:
            raw = self._chat_completion(system, user)
            if not raw:
                return neutral

            match = _re.search(r'\[.*\]', raw, _re.DOTALL)
            if match:
                results = _json.loads(match.group())
                # Validate and normalize
                scored = []
                for r in results:
                    scored.append({
                        "id": str(r.get("id", "")),
                        "technical_depth": max(0, min(100, int(r.get("technical_depth", 50)))),
                        "role_fit": max(0, min(100, int(r.get("role_fit", 50)))),
                        "evidence_strength": max(0, min(100, int(r.get("evidence_strength", 50)))),
                    })
                if scored:
                    return scored

            return neutral
        except Exception as e:
            logger.warning("LLM evidence analysis failed: %s", str(e))
            return neutral

    # ── HTTP Call ─────────────────────────────────────────────────

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[str]:
        """
        Call the Groq chat completions API with retry.

        Returns the assistant message content, or None on failure.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.post(url, json=payload, timeout=30)

                if resp.status_code == 429:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Groq rate limit hit, waiting %.1fs (attempt %d/%d)",
                        delay,
                        attempt,
                        MAX_RETRIES,
                    )
                    time.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return content.strip()

                logger.warning("Groq returned no choices")
                return None

            except requests.exceptions.RequestException as e:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Groq request failed (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    str(e),
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        logger.error("Groq request failed after %d retries", MAX_RETRIES)
        return None

