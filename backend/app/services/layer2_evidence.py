"""
VeriHire AI - Layer 2: Evidence Scoring & Consistency

Deterministic mathematical scoring (NO LLM) for Layer 2:
  - MathematicalScorer: GitHub score, DSA score, skill confidence
  - ConsistencyChecker: Claimed vs verified cross-checking, risk flags
  - EvidenceExtractor: Orchestrates evidence extraction + scoring for candidates

All scores are deterministic: same input -> same output.

Requirements: 6.1, 7.1, 8.1, 9.1-9.5, 10.1-10.5, 11.1-11.5, 12.1-12.5, 24.2
"""


import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models.candidate import RiskFlag, SkillConfidence
from app.models.evidence import CodeforcesStats, GitHubEvidence, LeetCodeStats
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Skill-to-language mapping ─────────────────────────────────────
# Maps resume skill names to GitHub language names for verification.
SKILL_TO_LANGUAGE: Dict[str, List[str]] = {
    "python": ["Python"],
    "javascript": ["JavaScript"],
    "typescript": ["TypeScript"],
    "java": ["Java"],
    "c++": ["C++"],
    "c#": ["C#"],
    "c": ["C"],
    "go": ["Go"],
    "rust": ["Rust"],
    "ruby": ["Ruby"],
    "php": ["PHP"],
    "swift": ["Swift"],
    "kotlin": ["Kotlin"],
    "scala": ["Scala"],
    "r": ["R"],
    "react": ["JavaScript", "TypeScript"],
    "node.js": ["JavaScript", "TypeScript"],
    "vue.js": ["JavaScript", "TypeScript", "Vue"],
    "angular": ["TypeScript"],
    "django": ["Python"],
    "flask": ["Python"],
    "spring boot": ["Java", "Kotlin"],
    "express": ["JavaScript", "TypeScript"],
    "html": ["HTML"],
    "css": ["CSS"],
    "tailwind css": ["CSS"],
}


class MathematicalScorer:
    """
    Deterministic scoring engine for Layer 2.

    All scores are pure functions of evidence data.
    """

    # ── GitHub Score (0-100) ──────────────────────────────────────

    def calculate_github_score(self, evidence: GitHubEvidence) -> int:
        """
        Calculate GitHub score from evidence.

        Formula:
            repo_score       (max 30) = min(30, repo_count * 0.6)
            diversity_score  (max 20) = min(20, language_count * 4)
            architecture     (max 30) = architecture_score * 0.3
            activity_score   (max 20) = based on last_active recency

        Preconditions:
            - evidence.verified is True

        Postconditions:
            - Returns integer 0-100
            - Deterministic (same input -> same output)
        """
        if not evidence.verified:
            return 0

        # Component 1: Repository count (max 30 pts)
        repo_score = min(30, evidence.repo_count * 0.6)

        # Component 2: Language diversity (max 20 pts)
        language_count = len(evidence.languages)
        diversity_score = min(20, language_count * 4)

        # Component 3: Architecture complexity (max 30 pts)
        architecture_score = evidence.architecture_score * 0.3

        # Component 4: Activity recency (max 20 pts)
        activity_score = self._calculate_activity_score(evidence.last_active)

        total = repo_score + diversity_score + architecture_score + activity_score
        result = max(0, min(100, round(total)))

        logger.debug(
            "GitHub score for %s: repo=%d div=%d arch=%d act=%d -> %d",
            evidence.username,
            round(repo_score),
            round(diversity_score),
            round(architecture_score),
            activity_score,
            result,
        )

        return result

    def _calculate_activity_score(self, last_active: str) -> int:
        """
        Calculate activity recency score (0-20).

        <= 7 days:   20 pts
        <= 30 days:  15 pts
        <= 90 days:  10 pts
        <= 180 days:  5 pts
        > 180 days:   0 pts
        """
        if not last_active or last_active == "Unknown":
            return 0

        try:
            last_dt = datetime.strptime(last_active, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            now = datetime.now(timezone.utc)
            days_ago = (now - last_dt).days

            if days_ago <= 7:
                return 20
            elif days_ago <= 30:
                return 15
            elif days_ago <= 90:
                return 10
            elif days_ago <= 180:
                return 5
            else:
                return 0
        except (ValueError, TypeError):
            return 0

    # ── DSA Score (0-100) ─────────────────────────────────────────

    def calculate_dsa_score(
        self,
        leetcode: Optional[LeetCodeStats],
        codeforces: Optional[CodeforcesStats],
    ) -> int:
        """
        Calculate DSA score from LeetCode and Codeforces evidence.

        LeetCode formula (0-100):
            rating_score     (max 50) = min(50, (rating / 3000) * 50)
            problems_score   (max 30) = min(30, (solved / 500) * 30)
            consistency      (max 20) = consistency * 0.2

        Codeforces formula (0-100):
            rating_score     (max 70) = min(70, (rating / 3000) * 70)
            contest_score    (max 30) = min(30, (contests / 50) * 30)

        Weighted: 60% LeetCode + 40% Codeforces (if both available).

        Postconditions:
            - Returns integer 0-100
        """
        lc_verified = leetcode is not None and leetcode.verified
        cf_verified = codeforces is not None and codeforces.verified

        leetcode_score = 0.0
        codeforces_score = 0.0

        # LeetCode component
        if lc_verified:
            rating_score = min(50, (leetcode.rating / 3000) * 50)
            problems_score = min(30, (leetcode.problems_solved / 500) * 30)
            consistency_score = leetcode.consistency * 0.2
            leetcode_score = rating_score + problems_score + consistency_score

        # Codeforces component
        if cf_verified:
            rating_score = min(70, (codeforces.rating / 3000) * 70)
            contest_score = min(30, (codeforces.contests_participated / 50) * 30)
            codeforces_score = rating_score + contest_score

        # Weighted average
        if lc_verified and cf_verified:
            final = (leetcode_score * 0.6) + (codeforces_score * 0.4)
        elif lc_verified:
            final = leetcode_score
        elif cf_verified:
            final = codeforces_score
        else:
            final = 0.0

        result = max(0, min(100, round(final)))

        logger.debug(
            "DSA score: LC=%.1f CF=%.1f -> %d",
            leetcode_score,
            codeforces_score,
            result,
        )

        return result

    # ── Skill Confidence (0-100 each) ─────────────────────────────

    def calculate_skill_scores(
        self,
        github_evidence: GitHubEvidence,
        claimed_skills: List[str],
    ) -> List[SkillConfidence]:
        """
        Compare claimed skills with GitHub language evidence.

        For each claimed skill:
            - claimed = 80 (default high claim from resume)
            - verified = GitHub language percentage (0-100)

        Skills not mappable to GitHub languages get verified=50 (neutral).

        Postconditions:
            - Returns one SkillConfidence per claimed skill
        """
        if not claimed_skills:
            return []

        # Build language percentage lookup from evidence
        lang_pct: Dict[str, int] = {}
        if github_evidence.verified:
            for lang in github_evidence.languages:
                lang_pct[lang.name.lower()] = lang.percentage

        results: List[SkillConfidence] = []
        for skill in claimed_skills:
            skill_lower = skill.lower().strip()

            # Find matching GitHub languages for this skill
            mapped_langs = SKILL_TO_LANGUAGE.get(skill_lower, [])

            if not mapped_langs or not github_evidence.verified:
                # No mapping or no evidence -> neutral score
                verified = 50
            else:
                # Use the highest percentage among matching languages
                max_pct = 0
                for lang in mapped_langs:
                    pct = lang_pct.get(lang.lower(), 0)
                    max_pct = max(max_pct, pct)

                # Scale: GitHub percentage -> verified score
                # 50%+ language = 100 verified, 0% = 0 verified
                verified = min(100, max_pct * 2)

            results.append(
                SkillConfidence(
                    name=skill,
                    claimed=80,  # Default claim from resume listing
                    verified=verified,
                )
            )

        return results


class ConsistencyChecker:
    """
    Cross-check resume claims against external evidence.

    Generates risk flags for inconsistencies and calculates
    an overall consistency score.
    """

    # ── Skill Consistency ─────────────────────────────────────────

    def check_skill_consistency(
        self,
        claimed_skills: List[str],
        github_evidence: GitHubEvidence,
    ) -> List[RiskFlag]:
        """
        Compare claimed skills with GitHub languages.

        Generates RiskFlag objects with severity:
            - "low":    10-20% gap
            - "medium": 20-40% gap
            - "high":   >40% gap

        Postconditions:
            - All flags have unique IDs
            - All flags reference valid skill names
        """
        if not github_evidence.verified or not claimed_skills:
            return []

        # Build language lookup
        lang_pct: Dict[str, int] = {}
        for lang in github_evidence.languages:
            lang_pct[lang.name.lower()] = lang.percentage

        flags: List[RiskFlag] = []
        seen_ids: set = set()

        for skill in claimed_skills:
            skill_lower = skill.lower().strip()
            mapped_langs = SKILL_TO_LANGUAGE.get(skill_lower, [])

            if not mapped_langs:
                continue  # Can't verify this skill via GitHub

            # Check if any matching language exists in GitHub
            max_pct = 0
            for lang in mapped_langs:
                max_pct = max(max_pct, lang_pct.get(lang.lower(), 0))

            # Calculate gap: claimed 80, verified = max_pct * 2 (scaled)
            verified_score = min(100, max_pct * 2)
            gap = max(0, 80 - verified_score)
            gap_pct = gap  # Gap is already on 0-100 scale

            if gap_pct > 40:
                severity = "high"
            elif gap_pct > 20:
                severity = "medium"
            elif gap_pct > 10:
                severity = "low"
            else:
                continue  # No significant gap

            flag_id = str(uuid.uuid4())[:8]
            while flag_id in seen_ids:
                flag_id = str(uuid.uuid4())[:8]
            seen_ids.add(flag_id)

            flags.append(
                RiskFlag(
                    id=flag_id,
                    severity=severity,
                    label=f"Skill gap: {skill}",
                    description=(
                        f"Claimed skill '{skill}' has limited GitHub evidence. "
                        f"GitHub language coverage: {max_pct}%. "
                        f"Gap: {gap_pct}%."
                    ),
                )
            )

        if flags:
            logger.debug(
                "Generated %d risk flags: %s",
                len(flags),
                [(f.severity, f.label) for f in flags],
            )

        return flags

    # ── Experience Consistency ────────────────────────────────────

    def check_experience_consistency(
        self,
        timeline: list,
        github_evidence: GitHubEvidence,
    ) -> List[RiskFlag]:
        """
        Cross-check experience timeline against GitHub activity.

        Flags if candidate claims recent experience but has no
        recent GitHub activity.
        """
        flags: List[RiskFlag] = []

        if not github_evidence.verified:
            return flags

        if github_evidence.last_active == "Unknown":
            return flags

        # Check if claims recent work but GitHub is dormant
        try:
            last_dt = datetime.strptime(
                github_evidence.last_active, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_inactive = (now - last_dt).days

            if days_inactive > 180 and timeline:
                flags.append(
                    RiskFlag(
                        id=str(uuid.uuid4())[:8],
                        severity="medium",
                        label="Dormant GitHub account",
                        description=(
                            f"GitHub last active {days_inactive} days ago, "
                            f"but candidate has {len(timeline)} timeline entries. "
                            "May indicate outdated profile."
                        ),
                    )
                )
        except (ValueError, TypeError):
            pass

        return flags

    # ── Overall Consistency Score ──────────────────────────────────

    def calculate_consistency_score(
        self,
        claimed_scores: Dict[str, float],
        verified_scores: Dict[str, float],
    ) -> float:
        """
        Calculate overall consistency score (0.0-1.0).

        Formula:
            consistency = max(0.0, 1.0 - (avg_gap / 100.0))

        If no comparisons possible, returns 0.5 (neutral).

        Postconditions:
            - Returns float between 0.0 and 1.0
        """
        gaps: List[float] = []

        for key in claimed_scores:
            if key in verified_scores:
                gap = abs(claimed_scores[key] - verified_scores[key])
                gaps.append(gap)

        if not gaps:
            return 0.5  # Neutral if no comparison possible

        avg_gap = sum(gaps) / len(gaps)
        consistency = max(0.0, min(1.0, 1.0 - (avg_gap / 100.0)))

        logger.debug(
            "Consistency: %d comparisons, avg_gap=%.1f, score=%.3f",
            len(gaps),
            avg_gap,
            consistency,
        )

        return round(consistency, 3)


# ── Link Parsing ──────────────────────────────────────────────────


def parse_online_links(online_links: str) -> Dict[str, str]:
    """
    Parse a comma-separated online_links string into platform -> username map.

    Supports GitHub, LeetCode, and Codeforces URLs.

    Returns:
        Dict mapping platform name to extracted username, e.g.:
        {"github": "sarahchen", "leetcode": "sarahchen"}
    """
    from app.integrations.github_client import GitHubClient
    from app.integrations.leetcode_client import LeetCodeClient
    from app.integrations.codeforces_client import CodeforcesClient

    result: Dict[str, str] = {}

    if not online_links:
        return result

    gh_user = GitHubClient.parse_username(online_links)
    if gh_user:
        result["github"] = gh_user

    lc_user = LeetCodeClient.parse_username(online_links)
    if lc_user:
        result["leetcode"] = lc_user

    cf_user = CodeforcesClient.parse_username(online_links)
    if cf_user:
        result["codeforces"] = cf_user

    return result


# ── Layer 2 Orchestrator ──────────────────────────────────────────


class EvidenceExtractor:
    """
    Orchestrates Layer 2: evidence extraction + mathematical scoring + LLM analysis.

    Pipeline:
        1. Math scoring on ALL candidates (parallel API calls)
        2. LLM analysis on top 50 only (batches of 5)
        3. Blend: final = math*0.4 + llm*0.6

    Uses ThreadPoolExecutor for parallel API calls across candidates.
    """

    def __init__(
        self,
        github_token: str = "",
        parallel_workers: int = 15,
        groq_model: str = "llama-3.3-70b-versatile",
        job_description: str = "",
        provider: str = "groq",
        ollama_base_url: Optional[str] = None,
    ):
        from app.integrations.github_client import GitHubClient
        from app.integrations.leetcode_client import LeetCodeClient
        from app.integrations.codeforces_client import CodeforcesClient

        self.github_client = GitHubClient(token=github_token)
        self.leetcode_client = LeetCodeClient()
        self.codeforces_client = CodeforcesClient()
        self.scorer = MathematicalScorer()
        self.checker = ConsistencyChecker()
        self.parallel_workers = parallel_workers
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model
        self.job_description = job_description
        self.provider = provider
        self.ollama_base_url = ollama_base_url

    # ── Main Entry Point ──────────────────────────────────────────

    def process_candidates(
        self,
        candidates: list,
    ) -> list:
        """
        Process a batch of CandidateMatch objects through Layer 2.

        For each candidate:
            1. Extract evidence from all platforms
            2. Calculate mathematical scores
            3. Run consistency checks
            4. Build ScoredCandidate

        Args:
            candidates: List of CandidateMatch from Layer 1.

        Returns:
            List of ScoredCandidate objects with scores and evidence.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from app.models.ranking import ScoredCandidate

        t_start = time.time()
        logger.info(
            "Layer 2 processing started: %d candidates",
            len(candidates),
        )

        scored_candidates: list = []

        # Process in parallel using thread pool
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as pool:
            future_to_candidate = {
                pool.submit(self._process_single, c): c
                for c in candidates
            }

            for future in as_completed(future_to_candidate):
                candidate = future_to_candidate[future]
                try:
                    scored = future.result()
                    scored_candidates.append(scored)
                except Exception as e:
                    logger.error(
                        "Failed to process candidate %s: %s",
                        candidate.candidate_id,
                        str(e),
                    )
                    # Create a minimal scored candidate on failure
                    scored_candidates.append(
                        ScoredCandidate(
                            candidate_id=candidate.candidate_id,
                            name=candidate.name,
                            email=candidate.email,
                            role=candidate.role,
                            skills=candidate.skills,
                            online_links=candidate.online_links,
                            timeline=candidate.timeline,
                            layer1_score=candidate.similarity_score,
                            github_score=0,
                            dsa_score=0,
                            consistency_score=0.5,
                        )
                    )

        elapsed = time.time() - t_start
        logger.info(
            "Layer 2 processing complete: %d candidates in %.2fs (%.2fs/candidate)",
            len(scored_candidates),
            elapsed,
            elapsed / len(candidates) if candidates else 0,
        )

        # Step 2: LLM analysis on top 50 (if LLM is available)
        has_llm = (self.provider == "ollama") or (self.provider == "groq" and self.groq_api_key)
        if has_llm and self.job_description:
            scored_candidates = self._apply_llm_analysis(scored_candidates)

        return scored_candidates

    # ── LLM Evidence Analysis ─────────────────────────────────────

    def _apply_llm_analysis(self, scored_candidates: list) -> list:
        """
        Run LLM analysis on top 50 candidates and blend scores.
        Math score (40%) + LLM score (60%). Rest keep pure math scores.
        """
        from app.integrations.groq_client import GroqClient
        from app.models.ranking import ScoredCandidate

        try:
            if self.provider == "ollama":
                client_url = (self.ollama_base_url or "http://localhost:11434").rstrip("/") + "/v1"
                client_key = "ollama"
                client_model = "llama3"
            else:
                client_url = "https://api.groq.com/openai/v1"
                client_key = self.groq_api_key
                client_model = self.groq_model
                
            client = GroqClient(
                api_key=client_key,
                model=client_model,
                base_url=client_url,
                max_tokens=1500,
            )
        except Exception as e:
            logger.warning("Could not create GroqClient for L2: %s", e)
            return scored_candidates

        # Sort by math PR to pick top 50
        sorted_all = sorted(
            scored_candidates,
            key=lambda c: c.github_score * 0.4 + c.dsa_score * 0.4 + c.consistency_score * 100 * 0.2,
            reverse=True,
        )
        LLM_TOP_K = 50
        top_candidates = sorted_all[:LLM_TOP_K]
        rest = sorted_all[LLM_TOP_K:]

        # LLM analysis in batches of 5
        BATCH_SIZE = 5
        id_to_llm = {}
        for i in range(0, len(top_candidates), BATCH_SIZE):
            batch = top_candidates[i : i + BATCH_SIZE]
            batch_data = []
            for c in batch:
                gh = c.github_evidence
                lc = c.leetcode_stats
                gh_str = (
                    f"Repos: {gh.repo_count}, Langs: "
                    + ", ".join(f"{l.name}({l.percentage}%)" for l in gh.languages[:5])
                    + f", Arch: {gh.architecture_score}/100, Active: {gh.last_active}"
                    if gh.verified else "Not verified"
                )
                lc_str = (
                    f"Solved: {lc.problems_solved} (E:{lc.easy} M:{lc.medium} H:{lc.hard}), Rating: {lc.rating}"
                    if lc.verified else "Not verified"
                )
                batch_data.append({
                    "id": c.candidate_id,
                    "name": c.name,
                    "github_data": gh_str,
                    "leetcode_data": lc_str,
                })
            results = client.analyze_evidence_batch(self.job_description, batch_data)
            for r in results:
                id_to_llm[r["id"]] = r
            logger.info("LLM evidence batch %d: %d scored", i // BATCH_SIZE + 1, len(results))

        # Blend scores
        blended = []
        for c in top_candidates:
            llm = id_to_llm.get(c.candidate_id)
            if llm:
                blended_gh = max(0, min(100, round(c.github_score * 0.4 + llm["technical_depth"] * 0.6)))
                blended_dsa = max(0, min(100, round(c.dsa_score * 0.4 + llm["evidence_strength"] * 0.6)))
                c_dict = c.model_dump()
                c_dict["github_score"] = blended_gh
                c_dict["dsa_score"] = blended_dsa
                c_dict["llm_analysis"] = {
                    "technical_depth": llm["technical_depth"],
                    "role_fit": llm["role_fit"],
                    "evidence_strength": llm["evidence_strength"],
                }
                blended.append(ScoredCandidate(**c_dict))
            else:
                blended.append(c)

        logger.info("LLM evidence complete: %d/%d enhanced", len(id_to_llm), len(top_candidates))
        return blended + rest

    # ── Single Candidate Processing ───────────────────────────────

    def _process_single(self, candidate) -> "ScoredCandidate":
        """Process a single candidate through evidence extraction + scoring."""
        from app.models.evidence import GitHubEvidence, LeetCodeStats, CodeforcesStats
        from app.models.ranking import ScoredCandidate

        # Step 1: Parse online links
        links = parse_online_links(candidate.online_links)
        logger.debug(
            "Candidate %s links: %s",
            candidate.name,
            list(links.keys()),
        )

        # Step 2: Extract evidence from each platform
        github_evidence = GitHubEvidence(verified=False)
        if "github" in links:
            try:
                github_evidence = self.github_client.extract_evidence(
                    links["github"]
                )
            except Exception as e:
                logger.warning(
                    "GitHub extraction failed for %s: %s",
                    candidate.name,
                    str(e),
                )

        leetcode_stats = LeetCodeStats(verified=False)
        if "leetcode" in links:
            try:
                leetcode_stats = self.leetcode_client.extract_evidence(
                    links["leetcode"]
                )
            except Exception as e:
                logger.warning(
                    "LeetCode extraction failed for %s: %s",
                    candidate.name,
                    str(e),
                )

        codeforces_stats = None
        if "codeforces" in links:
            try:
                codeforces_stats = self.codeforces_client.extract_evidence(
                    links["codeforces"]
                )
            except Exception as e:
                logger.warning(
                    "Codeforces extraction failed for %s: %s",
                    candidate.name,
                    str(e),
                )

        # Step 3: Calculate scores
        github_score = self.scorer.calculate_github_score(github_evidence)
        dsa_score = self.scorer.calculate_dsa_score(leetcode_stats, codeforces_stats)

        # Step 4: Skill confidence
        skill_scores = self.scorer.calculate_skill_scores(
            github_evidence,
            candidate.skills,
        )

        # Step 5: Consistency checks
        risk_flags = self.checker.check_skill_consistency(
            candidate.skills,
            github_evidence,
        )
        risk_flags.extend(
            self.checker.check_experience_consistency(
                candidate.timeline,
                github_evidence,
            )
        )

        # Step 6: Overall consistency score
        claimed = {"github": 80.0, "dsa": 80.0}
        verified = {"github": float(github_score), "dsa": float(dsa_score)}
        consistency_score = self.checker.calculate_consistency_score(
            claimed, verified
        )

        # Step 7: Build ScoredCandidate
        return ScoredCandidate(
            candidate_id=candidate.candidate_id,
            name=candidate.name,
            email=candidate.email,
            role=candidate.role,
            skills=candidate.skills,
            online_links=candidate.online_links,
            timeline=candidate.timeline,
            layer1_score=candidate.similarity_score,
            github_score=github_score,
            dsa_score=dsa_score,
            consistency_score=consistency_score,
            github_evidence=github_evidence,
            leetcode_stats=leetcode_stats,
            codeforces_stats=codeforces_stats,
            skill_scores=skill_scores,
            risk_flags=risk_flags,
        )

