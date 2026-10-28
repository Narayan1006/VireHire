# VeriHire v2: Project Spec

> Put this file at `docs/SPEC.md`. Every agent prompt starts with:
> "Read docs/SPEC.md. Do ONLY Milestone N. Follow the Working Rules."

## 1. What we are building

VeriHire ranks job candidates by **verifiable evidence**, not keyword matches.
A recruiter pastes a job description, uploads a candidate CSV, and gets a ranked list.
Each candidate shows a score, a confidence level, evidence (GitHub, LeetCode), and a plain-language explanation.

**Goals**
- A clean, deployed, working product at the existing repo URL and existing hosting links.
- Measured quality: a reproducible evaluation with real numbers in the README.
- One backend service, one database, simple to run and explain.

**Non-goals (do not build)**
- Automatic hire/reject decisions. The product is decision support; a human decides.
- Bring-your-own-key storage, multiple backends, Spring Boot, ChromaDB, torch, Firestore.
- Real-time features, payments, teams/roles.

## 2. Stack (fixed; do not substitute without asking)

| Area | Choice |
|---|---|
| Frontend | React + Vite + TypeScript + Tailwind + shadcn/ui, Inter font, light theme, one accent colour. Hosted on **Vercel** |
| Backend | One FastAPI service (Python 3.12), SQLAlchemy 2, Alembic, pydantic-settings. Hosted on Render as `verihire-api-v2` |
| Database | Supabase Postgres via the **Session pooler** connection string, with `pgvector`. Supabase is used ONLY as a database (no Supabase Auth/Storage/SDK) |
| Embeddings | `fastembed` (ONNX), model `BAAI/bge-small-en-v1.5` (384 dims). Computed once per candidate and stored |
| Retrieval | Postgres full-text search + vector similarity, merged with reciprocal rank fusion (RRF) |
| Evidence | GitHub GraphQL API (cached in Postgres), LeetCode public profile data as best-effort |
| LLM | Groq, used only to write explanations in structured JSON. It never decides the ranking |
| Jobs | FastAPI background tasks + a status column; the frontend polls |
| Auth | Email + password, argon2 or bcrypt, JWT access tokens |
| CI | GitHub Actions: ruff + pytest (api), `npm ci` + build (web), scheduled keep-alive ping |

## 3. Architecture

```
Browser (Vercel, React)
        |  HTTPS + JWT
        v
FastAPI (Render) ---- Groq (explanations)
        |        \--- GitHub GraphQL / LeetCode (evidence)
        v
Supabase Postgres (pgvector, RLS enabled on every table)
```

Pipeline for one job:
1. **Ingest**: parse CSV, validate, embed candidates, store.
2. **Retrieve**: hybrid search returns the top K candidates (default K = 200).
3. **Verify**: fetch evidence for the top N (default N = 50), with caching and a per-run time budget.
4. **Score**: deterministic score from retrieval + evidence, with a confidence value.
5. **Explain**: LLM writes a short explanation for the top M (default M = 20) from the stored evidence only.

## 4. Data model (initial)

- `users`: id (uuid), email (unique, lowercase), password_hash, created_at
- `jobs`: id, owner_id, title, description, status (`draft|processing|done|failed`), error, created_at
- `candidates`: id, job_id, name, email, resume_text, links (jsonb), embedding (vector(384)), search_tsv
- `evidence`: id, candidate_id, source (`github|leetcode`), status (`verified|unverified|error`), payload (jsonb), fetched_at
- `rankings`: id, job_id, candidate_id, retrieval_score, evidence_score, confidence, final_score, label, explanation (jsonb)

Rules: every table has Row Level Security **enabled**; every query is scoped to the authenticated owner; migrations are Alembic only.

## 5. Scoring rules

- "No evidence" is **unknown, not zero**. Unverified candidates are never penalized below the retrieval baseline.
- `evidence_score` (0-1) is built from hard-to-fake signals: non-fork repos, stars received, merged PRs to other people's repos, tests/README presence, recent activity, and problem-solving stats when available.
- `confidence` (0-1) reflects how much verified evidence exists.
- Initial formula (tuned in Milestone 4 using the evaluation, then frozen):
  `w = 0.4 * confidence`; `final = (1 - w) * retrieval_norm + w * evidence_score`
- Labels: `strong_match`, `needs_review`, `insufficient_evidence`. Thresholds are set in Milestone 4. There is no reject label.
- The LLM sees only stored evidence and the job description, returns JSON, and its output is shown as an explanation, never used to reorder results.

## 6. API surface (initial)

`POST /auth/register`, `POST /auth/login`, `GET /me`,
`POST /jobs`, `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/candidates` (CSV upload), `POST /jobs/{id}/run`, `GET /jobs/{id}/results`,
`GET /health`, `GET /version`.

## 7. UI pages

Login/Register, Jobs list, New job (description + CSV), Results (ranked table, score breakdown, evidence chips, confidence indicator, explanation drawer). Responsive, accessible, empty/loading/error states for every page.

## 8. Milestones and acceptance checklists

Each milestone is done only when it is **deployed, tested, and healthy**.

### M0: Skeleton deployed
- [ ] Monorepo layout `apps/api`, `apps/web`, `eval/`, `docs/`, `.github/workflows/`
- [ ] `/health` runs `SELECT 1` against Supabase; web shell shows healthy/unreachable
- [ ] Alembic 0001: pgvector + `users`, RLS enabled; test fails if any public table lacks RLS
- [ ] CI green; Render service and Vercel serve the skeleton

### M1: Auth and jobs
- [x] Register/login with JWT; password hashing; duplicate email rejected (verified via pytest and live curl test)
- [x] Job CRUD scoped to owner (user A cannot read user B's job; tested) (verified via pytest and live curl test)
- [x] Login, Jobs list, New job pages wired to the API (verified via tsc and npm run build)

### M2: Ingestion and retrieval
- [x] CSV upload with validation and clear error messages; size and row limits (verified via pytest in test_candidates_csv.py, frontend JobDetail.tsx, and live remote smoke test)
- [x] Embeddings stored once; hybrid retrieval with RRF (verified on SQLite, local Docker Postgres, and live smoke test on remote database with top 5 RRF ranking)
- [x] Peak memory stays under the Render instance limit on a 2,000-row CSV (measured 397.4 MB at batch size 16 vs 512 MB limit in benchmarks/benchmark_memory_2000.py)

### M3: Evidence and scoring
- [ ] GitHub GraphQL fetch with caching, timeouts, rate-limit handling
- [ ] LeetCode best-effort with graceful failure
- [ ] Scoring with unknown-vs-zero handling and confidence; unit tests for edge cases
- [ ] Results page shows breakdown, evidence chips, confidence

### M4: Evaluation and explanations
- [ ] `eval/` harness: labeled queries, baselines (keyword/BM25, embeddings only, hybrid, full pipeline)
- [ ] Reports NDCG@10 and precision@10, latency, and LLM calls per run
- [ ] Thresholds for labels set from the evaluation; formula frozen
- [ ] Explanations generated from stored evidence only, JSON-validated

### M5: Polish and launch
- [ ] README: pitch, architecture diagram, results table, limitations and fairness section, run/deploy steps
- [ ] Screenshots and a short demo video
- [ ] Keep-alive workflow; error monitoring via logs; final security pass
- [ ] Old URLs and the Vercel deployment point to the new app

## 9. Security rules

- No secrets in the repo, logs, or chat. Env var **names** only in docs.
- `DATABASE_URL` and `JWT_SECRET` are required; the app fails at startup if they are missing. No fallback secrets.
- CORS allows only the configured origins.
- Every table has RLS enabled; the API connects as the database owner and enforces ownership in code.
- Candidate data is personal data: no real candidate data in the repo; the evaluation uses synthetic or consented data.

## 10. Environment variables (names only)

API: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `GROQ_API_KEY`, `GITHUB_TOKEN`, `ENV`
Web: `VITE_API_URL`

## 11. Working rules for the coding agent

1. Read this file first. Do **only** the milestone named in the prompt; do not add features.
2. Work on a branch. **Do not commit or push.** Never print secret values.
3. Every change needs tests. Run them and report real output.
4. Cite `file:line` for claims. Say "unverified" instead of guessing.
5. Do not remove or weaken a test to make it pass; explain failures instead.
6. When finished, report: files changed (`git diff --stat`), test/build results, anything unverified, and env vars needed.