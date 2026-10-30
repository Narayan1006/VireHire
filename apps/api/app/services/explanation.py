"""
VeriHire v2 - Groq LLM Explanation Service (Milestone 4)
Generates structured JSON explanations strictly from stored evidence and job descriptions.

Design Rules (SPEC.md):
- The LLM NEVER decides or alters candidate rankings.
- It sees only stored evidence, job description, and deterministic scores.
- Output is validated JSON containing summary, strengths, gaps, evidence_assessment, and recommendation_rationale.
- Token Safety: GROQ_API_KEY is read only via Settings and never logged, printed, or sent anywhere except https://api.groq.com.
- Graceful Degradation: If no key is set or the call fails, a deterministic fallback explanation is generated.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Candidate, Evidence, Job, Ranking

logger = logging.getLogger("verihire.explanation")

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def build_explanation_prompt(
    job_title: str,
    job_description: str,
    candidate_name: str,
    resume_text: str,
    evidence_rows: List[Evidence | Dict[str, Any]],
    retrieval_score: float,
    final_score: float,
    label: str,
    reasons: List[str],
) -> tuple[str, str]:
    """
    Constructs the system and user prompts for Groq LLM explanation generation.
    Strictly forbids hallucination and enforces structured JSON output.
    """
    system_prompt = (
        "You are VeriHire AI Assistant, an objective technical recruitment evaluator.\n"
        "Your task is to produce a structured, factual evaluation of a candidate based SOLELY on "
        "the provided job description and verified evidence.\n\n"
        "CRITICAL RULES:\n"
        "1. You do NOT decide or change the candidate's ranking or score.\n"
        "2. Do NOT hallucinate or assume experience, metrics, or credentials not explicitly provided.\n"
        "3. If public evidence (GitHub or LeetCode) is absent or unverified, state that clearly.\n"
        "4. Output MUST be a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "1-2 sentence executive assessment of candidate fit",\n'
        '  "strengths": ["Bulleted factual strengths grounded in provided data"],\n'
        '  "gaps": ["Bulleted factual gaps or areas needing interview probing"],\n'
        '  "evidence_assessment": "Concise summary of verified public proof of work",\n'
        '  "recommendation_rationale": "Reasoning for the assigned deterministic label and score"\n'
        "}\n"
        "Respond ONLY with valid JSON."
    )

    # Format verified evidence
    evidence_lines = []
    for ev in evidence_rows:
        src = getattr(ev, "source", None) or (ev.get("source") if isinstance(ev, dict) else None)
        st = getattr(ev, "status", None) or (ev.get("status") if isinstance(ev, dict) else None)
        pl = getattr(ev, "payload", None) or (ev.get("payload") if isinstance(ev, dict) else {})
        usr = getattr(ev, "username", None) or (ev.get("username") if isinstance(ev, dict) else None)

        if st == "verified" and pl:
            if src == "github":
                stars = pl.get("total_stars", 0)
                prs = pl.get("merged_external_prs", 0)
                repos = pl.get("public_repos_count", 0)
                commits = pl.get("commit_contributions", 0)
                langs = list((pl.get("languages_histogram") or {}).keys())[:8]
                evidence_lines.append(
                    f"- GitHub (@{usr}): {stars} stars received, {prs} external merged PRs, "
                    f"{commits} commits in last year, {repos} public repos. Top languages: {', '.join(langs) or 'None'}"
                )
            elif src == "leetcode":
                solved = pl.get("total_solved", 0)
                h = pl.get("hard_solved", 0)
                m = pl.get("medium_solved", 0)
                e = pl.get("easy_solved", 0)
                rating = pl.get("contest_rating")
                rating_str = f", contest rating: {round(rating)}" if rating else ""
                evidence_lines.append(
                    f"- LeetCode (@{usr}): {solved} solved ({h} hard, {m} medium, {e} easy){rating_str}"
                )
        else:
            reason = getattr(ev, "reason", None) or (ev.get("reason") if isinstance(ev, dict) else "unverified")
            evidence_lines.append(f"- {src}: Unverified / not found ({reason})")

    if not evidence_lines:
        evidence_lines.append("- No public profiles found or verified.")

    evidence_text = "\n".join(evidence_lines)
    reasons_text = "\n".join(f"- {r}" for r in reasons) or "- Baseline semantic match."

    user_prompt = (
        f"JOB TITLE: {job_title}\n\n"
        f"JOB REQUIREMENTS:\n{job_description[:3000]}\n\n"
        f"CANDIDATE: {candidate_name}\n"
        f"DETERMINISTIC EVALUATION METRICS:\n"
        f"- Final Score: {round(final_score * 100, 1)}%\n"
        f"- Semantic Retrieval Match: {round(retrieval_score * 100, 1)}%\n"
        f"- Assigned Label: {label}\n\n"
        f"DATA-DERIVED PROOF POINTS:\n{reasons_text}\n\n"
        f"VERIFIED PUBLIC EVIDENCE:\n{evidence_text}\n\n"
        f"RESUME EXCERPT:\n{resume_text[:2000]}\n\n"
        "Generate the structured JSON explanation now."
    )

    return system_prompt, user_prompt


def generate_deterministic_fallback_explanation(
    candidate_name: str,
    job_title: str,
    retrieval_score: float,
    final_score: float,
    label: str,
    reasons: List[str],
    evidence_rows: List[Evidence | Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Produces a clean, accurate structured explanation without LLM network access.
    Used as an automatic fallback when GROQ_API_KEY is not set or network fails.
    """
    label_friendly = {
        "strong_match": "Strong Match",
        "needs_review": "Needs Review",
        "insufficient_evidence": "Insufficient Evidence",
    }.get(label, "Candidate")

    has_verified = any(
        (getattr(e, "status", None) or (e.get("status") if isinstance(e, dict) else None)) == "verified"
        for e in evidence_rows
    )

    strengths = [r for r in reasons if "No verified" not in r]
    if not strengths:
        strengths = [f"Semantic resume alignment of {round(retrieval_score * 100, 1)}% for {job_title}."]

    gaps = []
    if not has_verified:
        gaps.append("No verified public GitHub or LeetCode proof was found; candidate evaluation relies on resume claims.")
        gaps.append("Recommend live technical screening or code walkthrough to confirm hands-on implementation skills.")
    else:
        gaps.append("Verify architectural depth and communication during live technical interview.")

    summary = (
        f"{candidate_name} is evaluated as a {label_friendly} with a final deterministic score "
        f"of {round(final_score * 100, 1)}% against the {job_title} role."
    )

    if has_verified:
        evidence_assessment = (
            f"Public evidence verified across {len([e for e in evidence_rows if (getattr(e, 'status', None) or (e.get('status') if isinstance(e, dict) else None)) == 'verified'])} "
            f"platform(s) providing tangible proof of engineering contributions."
        )
    else:
        evidence_assessment = (
            "No verified public proof of work found. Scored strictly by retrieval baseline without penalty."
        )

    recommendation_rationale = (
        f"Assigned label '{label}' from deterministic multi-signal scoring combining semantic retrieval "
        f"({round(retrieval_score * 100, 1)}%) and verifiable evidence weighting."
    )

    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "evidence_assessment": evidence_assessment,
        "recommendation_rationale": recommendation_rationale,
        "generated_by": "deterministic_fallback",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def request_groq_explanation(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "llama-3.3-70b-versatile",
    timeout_seconds: float = 20.0,
) -> Dict[str, Any]:
    """
    Sends an async chat completion request to Groq with JSON mode enabled.
    Never prints or logs the api_key.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1000,
    }

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(GROQ_CHAT_COMPLETIONS_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        # Validate schema keys
        required_keys = {"summary", "strengths", "gaps", "evidence_assessment", "recommendation_rationale"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError(f"Groq response missing required keys: {required_keys - set(parsed.keys())}")

        parsed["generated_by"] = f"groq:{model}"
        parsed["timestamp"] = datetime.now(timezone.utc).isoformat()
        return parsed


async def generate_candidate_explanation(
    job_title: str,
    job_description: str,
    candidate_name: str,
    resume_text: str,
    evidence_rows: List[Evidence | Dict[str, Any]],
    retrieval_score: float,
    final_score: float,
    label: str,
    reasons: List[str],
    settings: Optional[Settings] = None,
) -> tuple[Dict[str, Any], bool]:
    """
    Generates structured explanation for a candidate.
    Returns (explanation_dict, was_llm_used).
    Gracefully falls back to deterministic generation if no key or error occurs.
    """
    s = settings or get_settings()
    api_key = s.raw_groq_api_key

    if not api_key:
        logger.info("GROQ_API_KEY not set; using deterministic explanation fallback")
        fallback = generate_deterministic_fallback_explanation(
            candidate_name=candidate_name,
            job_title=job_title,
            retrieval_score=retrieval_score,
            final_score=final_score,
            label=label,
            reasons=reasons,
            evidence_rows=evidence_rows,
        )
        return fallback, False

    system_prompt, user_prompt = build_explanation_prompt(
        job_title=job_title,
        job_description=job_description,
        candidate_name=candidate_name,
        resume_text=resume_text,
        evidence_rows=evidence_rows,
        retrieval_score=retrieval_score,
        final_score=final_score,
        label=label,
        reasons=reasons,
    )

    try:
        explanation = await request_groq_explanation(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=api_key,
            model=s.groq_model,
        )
        return explanation, True
    except Exception as exc:
        logger.warning("Groq explanation call failed; falling back to deterministic: %s", type(exc).__name__)
        fallback = generate_deterministic_fallback_explanation(
            candidate_name=candidate_name,
            job_title=job_title,
            retrieval_score=retrieval_score,
            final_score=final_score,
            label=label,
            reasons=reasons,
            evidence_rows=evidence_rows,
        )
        return fallback, False


def explain_top_candidates_for_job(
    job_id: uuid.UUID,
    db: Session,
    top_m: Optional[int] = None,
    settings: Optional[Settings] = None,
) -> int:
    """
    Generates and persists explanations for the top M ranked candidates of a job.
    Uses asyncio to execute the LLM/fallback generation.
    Returns the number of candidates explained.
    """
    import asyncio

    s = settings or get_settings()
    m_limit = top_m or s.explanation_top_m

    job = db.get(Job, job_id)
    if not job:
        return 0

    # Fetch top M ranked candidates ordered by final_score / rank
    rankings_query = (
        select(Ranking, Candidate)
        .join(Candidate, Ranking.candidate_id == Candidate.id)
        .where(Ranking.job_id == job_id)
        .order_by(
            Ranking.final_score.desc().nullslast(),
            Ranking.retrieval_score.desc(),
            Ranking.rank.asc(),
        )
        .limit(m_limit)
    )
    ranked_candidates = db.execute(rankings_query).all()
    if not ranked_candidates:
        return 0

    candidate_ids = [c.id for _, c in ranked_candidates]
    evidence_query = select(Evidence).where(Evidence.candidate_id.in_(candidate_ids))
    evidence_rows = db.execute(evidence_query).scalars().all()

    evidence_by_cand: Dict[uuid.UUID, List[Evidence]] = {cid: [] for cid in candidate_ids}
    for ev in evidence_rows:
        evidence_by_cand[ev.candidate_id].append(ev)

    async def _explain_all():
        explained = 0
        for ranking, candidate in ranked_candidates:
            cand_evidence = evidence_by_cand.get(candidate.id, [])
            reasons = (ranking.breakdown or {}).get("reasons", [])
            final_sc = ranking.final_score if ranking.final_score is not None else ranking.retrieval_score
            label_val = ranking.label or "insufficient_evidence"

            explanation_dict, _ = await generate_candidate_explanation(
                job_title=job.title,
                job_description=job.description,
                candidate_name=candidate.name,
                resume_text=candidate.resume_text,
                evidence_rows=cand_evidence,
                retrieval_score=ranking.retrieval_score,
                final_score=final_sc,
                label=label_val,
                reasons=reasons,
                settings=s,
            )

            ranking.explanation = explanation_dict
            explained += 1

        db.commit()
        return explained

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _explain_all()).result()
        else:
            return loop.run_until_complete(_explain_all())
    except RuntimeError:
        return asyncio.run(_explain_all())
