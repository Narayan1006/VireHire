"""
VeriHire v2 - Pure Deterministic Scoring Engine (Milestone 3B)
Computes multi-signal evidence scoring, confidence weighting,
skill overlap matching, and explainable breakdowns without DB or network access.

All weights, saturation caps, and thresholds are provisional and configurable
via Settings (SCORING_* env vars), to be tuned against the evaluation benchmark in M4.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import Settings, get_settings
from app.data.tech_vocabulary import extract_technologies


def saturating_transform(val: float | int, cap: float | int) -> float:
    """
    Saturating log-transform: x -> min(1.0, log1p(x) / log1p(cap)).
    Guarantees strict 0-1 bounds and prevents vanity metrics from dominating.
    """
    if val <= 0 or cap <= 0:
        return 0.0
    val_f = float(val)
    cap_f = float(cap)
    ratio = math.log1p(val_f) / math.log1p(cap_f)
    return min(1.0, max(0.0, ratio))


def compute_github_signals(
    payload: Dict[str, Any],
    settings: Optional[Settings] = None,
    now: Optional[datetime] = None,
) -> Dict[str, float]:
    """
    Extracts normalized 0-1 GitHub signal components from stored payload:
    - external_collaboration: merged external PRs and code reviews
    - repo_impact: total stars, forks, and followers (log-saturated)
    - sustained_activity: commit contributions, recency of repo pushes, account age
    - breadth: distinct languages in histogram, public repo count
    Uses ONLY keys present in the stored payload.
    """
    s = settings or get_settings()
    ref_time = now or datetime.now(timezone.utc)

    # 1. External Collaboration
    merged_prs = payload.get("merged_external_prs", 0) or 0
    reviews = payload.get("review_contributions", 0) or 0

    sat_prs = saturating_transform(merged_prs, s.scoring_cap_external_prs)
    sat_rev = saturating_transform(reviews, s.scoring_cap_reviews)
    ext_collab = 0.75 * sat_prs + 0.25 * sat_rev

    # 2. Repository Impact
    total_stars = payload.get("total_stars", 0) or 0
    total_forks = payload.get("total_forks", 0) or 0
    followers = payload.get("followers_count", 0) or 0

    sat_stars = saturating_transform(total_stars, s.scoring_cap_stars)
    sat_forks = saturating_transform(total_forks, s.scoring_cap_forks)
    sat_followers = saturating_transform(followers, s.scoring_cap_followers)
    repo_impact = 0.65 * sat_stars + 0.20 * sat_forks + 0.15 * sat_followers

    # 3. Sustained Activity
    commits = payload.get("commit_contributions", 0) or 0
    sat_commits = saturating_transform(commits, s.scoring_cap_commits)

    # Recency of push dates in top_repos
    top_repos: List[Dict[str, Any]] = payload.get("top_repos", []) or []
    recency_scores = []
    for r in top_repos:
        pushed_at_str = r.get("pushed_at")
        if pushed_at_str:
            try:
                # Handle ISO timestamps with Z or offset
                p_dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                days_since = max(0.0, (ref_time - p_dt).total_seconds() / 86400.0)
                if days_since <= 90:
                    recency_scores.append(1.0)
                elif days_since <= 180:
                    recency_scores.append(0.7)
                elif days_since <= 365:
                    recency_scores.append(0.4)
                else:
                    recency_scores.append(0.1)
            except Exception:
                recency_scores.append(0.1)
        else:
            recency_scores.append(0.1)

    avg_recency = (sum(recency_scores) / len(recency_scores)) if recency_scores else 0.0

    # Account age
    created_at_str = payload.get("created_at")
    age_days = 0.0
    if created_at_str:
        try:
            c_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            age_days = max(0.0, (ref_time - c_dt).total_seconds() / 86400.0)
        except Exception:
            age_days = 0.0
    sat_age = saturating_transform(age_days, s.scoring_cap_account_age_days)

    sustained_activity = 0.45 * sat_commits + 0.30 * avg_recency + 0.25 * sat_age

    # 4. Breadth
    lang_hist = payload.get("language_histogram", {}) or {}
    distinct_langs = len(lang_hist)
    sat_langs = saturating_transform(distinct_langs, 6)

    repos_count = payload.get("public_repos_count", 0) or 0
    sat_repos = saturating_transform(repos_count, s.scoring_cap_repos)

    breadth = 0.50 * sat_langs + 0.50 * sat_repos

    return {
        "external_collaboration": min(1.0, max(0.0, ext_collab)),
        "repo_impact": min(1.0, max(0.0, repo_impact)),
        "sustained_activity": min(1.0, max(0.0, sustained_activity)),
        "breadth": min(1.0, max(0.0, breadth)),
    }


def compute_leetcode_signals(
    payload: Dict[str, Any],
    settings: Optional[Settings] = None,
) -> Optional[float]:
    """
    Computes normalized 0-1 score for LeetCode problem solving.
    Returns None if payload is empty or unverified.
    """
    if not payload:
        return None

    s = settings or get_settings()
    easy = payload.get("easy_solved", 0) or 0
    medium = payload.get("medium_solved", 0) or 0
    hard = payload.get("hard_solved", 0) or 0
    rating = payload.get("contest_rating")

    sat_easy = saturating_transform(easy, s.scoring_cap_leetcode_medium)
    sat_medium = saturating_transform(medium, s.scoring_cap_leetcode_medium)
    sat_hard = saturating_transform(hard, s.scoring_cap_leetcode_hard)

    # Hard problems weighted significantly more
    solved_score = 0.15 * sat_easy + 0.40 * sat_medium + 0.45 * sat_hard

    if rating and isinstance(rating, (int, float)) and rating > 1000:
        # Benchmark rating: 1200 base up to 2400 (guardian/grandmaster)
        rating_score = min(1.0, max(0.0, (rating - 1200.0) / 1200.0))
        final_lc = 0.70 * solved_score + 0.30 * rating_score
    else:
        final_lc = solved_score

    return min(1.0, max(0.0, final_lc))


def compute_skill_overlap(
    job_description: str,
    github_payload: Dict[str, Any],
) -> Tuple[Optional[float], Set[str]]:
    """
    Computes 0-1 overlap between technologies required in job description
    and technologies demonstrated in candidate's GitHub repositories and languages.
    Returns (overlap_ratio, matched_technologies_set).
    If the job description mentions no vocabulary terms, returns (None, empty_set).
    """
    required_techs = extract_technologies(job_description)
    if not required_techs:
        return None, set()

    # Candidate technologies from language histogram and repo names/languages
    candidate_tech_text_parts = []

    lang_hist = github_payload.get("language_histogram", {}) or {}
    for lang in lang_hist.keys():
        candidate_tech_text_parts.append(str(lang))

    top_repos: List[Dict[str, Any]] = github_payload.get("top_repos", []) or []
    for r in top_repos:
        if r.get("name"):
            candidate_tech_text_parts.append(str(r["name"]))
        if r.get("language"):
            candidate_tech_text_parts.append(str(r["language"]))

    candidate_text = " ".join(candidate_tech_text_parts)
    candidate_techs = extract_technologies(candidate_text)

    matched = required_techs.intersection(candidate_techs)
    overlap = len(matched) / len(required_techs)
    return min(1.0, max(0.0, float(overlap))), matched


def compute_confidence(
    github_status: str,
    leetcode_status: str,
    github_payload: Dict[str, Any],
    leetcode_payload: Dict[str, Any],
    settings: Optional[Settings] = None,
    now: Optional[datetime] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Computes confidence score in [0.0, 1.0].
    - 0.0 when nothing is verified.
    - GitHub verified contributes up to 0.7 scaled by data richness.
    - LeetCode verified contributes up to 0.3 scaled by solved count.
    - Sum is capped at 1.0.
    """
    s = settings or get_settings()
    ref_time = now or datetime.now(timezone.utc)

    gh_conf = 0.0
    lc_conf = 0.0

    if github_status == "verified" and github_payload:
        repos_sampled = github_payload.get("owned_repos_sampled", 0) or 0
        commits = github_payload.get("commit_contributions", 0) or 0
        prs = github_payload.get("pr_contributions", 0) or 0
        reviews = github_payload.get("review_contributions", 0) or 0
        total_activity = commits + prs + reviews

        created_at_str = github_payload.get("created_at")
        age_days = 0.0
        if created_at_str:
            try:
                c_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                age_days = max(0.0, (ref_time - c_dt).total_seconds() / 86400.0)
            except Exception:
                age_days = 0.0

        sat_sampled = saturating_transform(repos_sampled, 10)
        sat_activity = saturating_transform(total_activity, 500)
        sat_age = saturating_transform(age_days, s.scoring_cap_account_age_days)

        richness = 0.35 * sat_sampled + 0.35 * sat_activity + 0.30 * sat_age
        # Baseline confidence 0.20 when verified, scaling up to 0.70 with richness
        gh_conf = 0.70 * (0.25 + 0.75 * richness)

    if leetcode_status == "verified" and leetcode_payload:
        solved = leetcode_payload.get("total_solved", 0) or 0
        sat_solved = saturating_transform(solved, 100)
        # Baseline confidence 0.25 when verified, scaling up to 0.30 with solved count
        lc_conf = 0.30 * (0.25 + 0.75 * sat_solved)

    total_conf = min(1.0, gh_conf + lc_conf)
    if github_status != "verified" and leetcode_status != "verified":
        total_conf = 0.0

    return total_conf, {"github": gh_conf, "leetcode": lc_conf}


def compute_evidence_score(
    components: Dict[str, Optional[float]],
    settings: Optional[Settings] = None,
) -> Tuple[Optional[float], Dict[str, float]]:
    """
    Weighted mean of available components with weights renormalized across components that exist.
    Returns (evidence_score, weights_used).
    Returns (None, {}) if no verified components exist.
    """
    s = settings or get_settings()

    default_weights = {
        "external_collaboration": s.scoring_weight_external_collaboration,
        "repo_impact": s.scoring_weight_repo_impact,
        "sustained_activity": s.scoring_weight_sustained_activity,
        "breadth": s.scoring_weight_breadth,
        "skill_overlap": s.scoring_weight_skill_overlap,
        "leetcode": s.scoring_weight_leetcode,
    }

    active_components = {k: v for k, v in components.items() if v is not None}
    if not active_components:
        return None, {}

    total_weight = sum(default_weights.get(k, 0.0) for k in active_components.keys())
    if total_weight <= 0:
        return None, {}

    normalized_weights = {k: default_weights[k] / total_weight for k in active_components.keys()}
    weighted_sum = sum(active_components[k] * normalized_weights[k] for k in active_components.keys())

    return min(1.0, max(0.0, weighted_sum)), normalized_weights


def score_candidate(
    retrieval_score: float,
    job_description: str,
    evidence_rows: List[Any],
    settings: Optional[Settings] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Pure candidate scoring function.
    Given retrieval score, job description, and evidence rows (from Evidence model or dicts):
    1. Extracts GitHub & LeetCode signals
    2. Computes skill overlap
    3. Calculates confidence & evidence score
    4. Computes final_score via (1 - w) * retrieval_norm + w * evidence_score
       where w = SCORING_MAX_EVIDENCE_WEIGHT * confidence.
       If evidence_score is None: w = 0 -> final_score == retrieval_norm exactly.
    5. Assigns label (insufficient_evidence, strong_match, needs_review)
    6. Builds data-derived reasons list.
    """
    s = settings or get_settings()
    ref_time = now or datetime.now(timezone.utc)
    retrieval_norm = min(1.0, max(0.0, float(retrieval_score)))

    # Parse evidence rows
    gh_status = "none"
    gh_payload: Dict[str, Any] = {}
    lc_status = "none"
    lc_payload: Dict[str, Any] = {}

    for ev in evidence_rows:
        src = getattr(ev, "source", None) or (ev.get("source") if isinstance(ev, dict) else None)
        st = getattr(ev, "status", None) or (ev.get("status") if isinstance(ev, dict) else None)
        pl = getattr(ev, "payload", None) or (ev.get("payload") if isinstance(ev, dict) else {})
        if src == "github":
            gh_status = st or "none"
            gh_payload = pl or {}
        elif src == "leetcode":
            lc_status = st or "none"
            lc_payload = pl or {}

    components: Dict[str, Optional[float]] = {
        "external_collaboration": None,
        "repo_impact": None,
        "sustained_activity": None,
        "breadth": None,
        "skill_overlap": None,
        "leetcode": None,
    }
    reasons: List[str] = []
    matched_techs: Set[str] = set()

    # 1. GitHub Signals
    if gh_status == "verified" and gh_payload:
        gh_sigs = compute_github_signals(gh_payload, settings=s, now=ref_time)
        components["external_collaboration"] = gh_sigs["external_collaboration"]
        components["repo_impact"] = gh_sigs["repo_impact"]
        components["sustained_activity"] = gh_sigs["sustained_activity"]
        components["breadth"] = gh_sigs["breadth"]

        overlap_val, matched_techs = compute_skill_overlap(job_description, gh_payload)
        components["skill_overlap"] = overlap_val

        # Generate data-derived reasons from GitHub facts
        merged_prs = gh_payload.get("merged_external_prs", 0) or 0
        if merged_prs > 0:
            reasons.append(f"{merged_prs} merged pull requests to other people's repositories")

        stars = gh_payload.get("total_stars", 0) or 0
        if stars > 0:
            reasons.append(f"{stars} total GitHub stars received across repositories")

        commits = gh_payload.get("commit_contributions", 0) or 0
        if commits > 0:
            reasons.append(f"{commits} commits in the last year")

        if matched_techs:
            tech_list = ", ".join(sorted(matched_techs))
            reasons.append(f"Demonstrated experience in {len(matched_techs)} job-relevant technologies ({tech_list})")

        public_repos = gh_payload.get("public_repos_count", 0) or 0
        if public_repos > 0:
            reasons.append(f"{public_repos} public repositories owned")

    # 2. LeetCode Signals
    if lc_status == "verified" and lc_payload:
        lc_score = compute_leetcode_signals(lc_payload, settings=s)
        components["leetcode"] = lc_score

        total_solved = lc_payload.get("total_solved", 0) or 0
        if total_solved > 0:
            diff_parts = []
            h = lc_payload.get("hard_solved", 0) or 0
            m = lc_payload.get("medium_solved", 0) or 0
            e = lc_payload.get("easy_solved", 0) or 0
            if h > 0:
                diff_parts.append(f"{h} hard")
            if m > 0:
                diff_parts.append(f"{m} medium")
            if e > 0:
                diff_parts.append(f"{e} easy")
            diff_str = f" ({', '.join(diff_parts)})" if diff_parts else ""
            reasons.append(f"{total_solved} LeetCode problems solved{diff_str}")

        rating = lc_payload.get("contest_rating")
        if rating and isinstance(rating, (int, float)) and rating > 1000:
            reasons.append(f"LeetCode contest rating of {round(rating)}")

    # 3. Confidence & Evidence Score
    conf, conf_parts = compute_confidence(
        gh_status, lc_status, gh_payload, lc_payload, settings=s, now=ref_time
    )
    ev_score, weights_used = compute_evidence_score(components, settings=s)

    # 4. Final Score (No penalty for unknown evidence: w=0 if no verified evidence)
    if ev_score is None:
        w = 0.0
        final_score = retrieval_norm
    else:
        w = s.scoring_max_evidence_weight * conf
        final_score = (1.0 - w) * retrieval_norm + w * ev_score

    final_score = min(1.0, max(0.0, final_score))

    # 5. Label
    if conf < s.scoring_min_confidence:
        label = "insufficient_evidence"
    elif final_score >= s.scoring_strong_threshold:
        label = "strong_match"
    else:
        label = "needs_review"

    # Fallback reason when no verified evidence is available
    if not reasons:
        reasons.append("No verified public proof of work found; scored by retrieval baseline alone")

    breakdown = {
        "components": components,
        "weights": weights_used,
        "w": round(w, 4),
        "confidence": round(conf, 4),
        "confidence_parts": {k: round(v, 4) for k, v in conf_parts.items()},
        "retrieval_norm": round(retrieval_norm, 4),
        "evidence_score": round(ev_score, 4) if ev_score is not None else None,
        "final_score": round(final_score, 4),
        "label": label,
        "reasons": reasons,
    }

    return {
        "evidence_score": ev_score,
        "confidence": conf,
        "final_score": final_score,
        "label": label,
        "breakdown": breakdown,
    }


def score_job(job_id: Any, db: Any, settings: Optional[Settings] = None) -> int:
    """
    Loads a job's rankings and evidence rows, computes deterministic scores,
    and updates each ranking's evidence_score, confidence, final_score, label,
    and breakdown. Candidates without evidence rows are scored as unknown.
    Returns the count of candidates scored.
    """
    from sqlalchemy import select
    from app.models import Evidence, Job, Ranking

    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job is None:
        return 0

    rankings = db.execute(
        select(Ranking).where(Ranking.job_id == job_id).order_by(Ranking.rank.asc())
    ).scalars().all()
    if not rankings:
        return 0

    candidate_ids = [r.candidate_id for r in rankings]
    evidence_rows = db.execute(
        select(Evidence).where(Evidence.candidate_id.in_(candidate_ids))
    ).scalars().all()

    evidence_by_cand: Dict[Any, List[Evidence]] = {cid: [] for cid in candidate_ids}
    for ev in evidence_rows:
        evidence_by_cand[ev.candidate_id].append(ev)

    s = settings or get_settings()

    for r in rankings:
        ev_list = evidence_by_cand.get(r.candidate_id, [])
        scored = score_candidate(
            retrieval_score=r.retrieval_score,
            job_description=job.description,
            evidence_rows=ev_list,
            settings=s,
        )
        r.evidence_score = scored["evidence_score"]
        r.confidence = scored["confidence"]
        r.final_score = scored["final_score"]
        r.label = scored["label"]
        r.breakdown = scored["breakdown"]

    db.commit()
    return len(rankings)
