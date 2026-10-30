# VeriHire

VeriHire is an evidence-backed hiring intelligence platform that ranks technical job candidates by verifiable public proof of work—such as GitHub contributions, pull requests, repository quality, and LeetCode problem-solving stats—rather than self-reported resume claims or keyword matching. Recruiter teams provide a job description and a candidate dataset to receive an explainable, confidence-weighted candidate ranking where lack of evidence is treated as unknown rather than zero, ensuring decisions are grounded in demonstrable skill.

## Architecture

```mermaid
graph TD
    Client["Browser (React + Vite + Tailwind + shadcn/ui)<br/>Hosted on Vercel"]
    API["VeriHire API (FastAPI, Python 3.12)<br/>Hosted on Render (verihire-api-v2)"]
    DB[("PostgreSQL 16 + pgvector<br/>Supabase Session Pooler (port 5432)")]
    Keepalive["GitHub Actions (Keepalive Workflow)<br/>Pings /health every 3 days"]

    Client -->|"GET /health, /version<br/>REST API"| API
    API -->|"SQLAlchemy 2 + psycopg 3<br/>prepare_threshold: None"| DB
    Keepalive -->|"curl -fsS API_HEALTH_URL"| API
```

## Local Development Quickstart

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+ and npm

### Steps

1. **Start the local Postgres database with pgvector:**
   ```bash
   docker compose up -d
   ```

2. **Set up the Backend API (`apps/api`):**
   ```bash
   cd apps/api
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure local environment variables:**
   Create `apps/api/.env`:
   ```bash
   DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/verihire
   JWT_SECRET=your-local-development-jwt-secret-min-32-chars
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the API server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Set up and start the Web Frontend (`apps/web`):**
   ```bash
   cd ../web
   npm install
   ```
   Create `apps/web/.env`:
   ```bash
   VITE_API_URL=http://localhost:8000
   ```
   Start the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` to see the VeriHire shell page and real-time API health status.

---

## Environment Variables

| Variable Name | Service | Purpose |
|---|---|---|
| `DATABASE_URL` | API | Connection string targeting PostgreSQL (`postgresql+psycopg://...`) |
| `JWT_SECRET` | API | Secret key used for cryptographic signing of JWT tokens |
| `CORS_ORIGINS` | API | Comma-delimited list of allowed CORS client origins |
| `ENV` | API | Application environment identifier (`development`, `production`) |
| `GROQ_API_KEY` | API | (Milestone 4+) API key for LLM structured explanation generation |
| `GITHUB_TOKEN` | API | (Milestone 3+) GitHub GraphQL token for evidence verification |
| `VITE_API_URL` | Web | Base URL pointing to the deployed or local FastAPI backend |
| `API_HEALTH_URL` | GitHub Actions | Repository variable targeted by the keepalive ping workflow |

> **Note**: Never store or commit actual secret values to version control. Set these values securely in the Render dashboard and Vercel environment configuration.

---

## Deploying to Vercel (Frontend)

The frontend (`apps/web`) is deployed via [Vercel](https://vercel.com).

| Vercel Setting | Value |
|---|---|
| Root Directory | `apps/web` |
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |

**Environment Variable to set in Vercel dashboard:**

| Name | Value |
|---|---|
| `VITE_API_URL` | Your Render API URL, e.g. `https://verihire-api-v2.onrender.com` |

The `apps/web/vercel.json` handles the SPA rewrite (all non-file routes → `/index.html`). No additional configuration is needed.

**After deploying**, copy the Vercel URL (e.g. `https://<project>.vercel.app`) and add it to `CORS_ORIGINS` in the Render service environment.

---

## Database Architecture & Operational Notes

### 1. Supabase as a Pure PostgreSQL Database
Supabase is utilized strictly as a managed PostgreSQL instance with `pgvector` enabled. VeriHire does **not** use the Supabase JavaScript/Python client SDKs, Supabase Auth, or Supabase Storage. All database access is governed by SQLAlchemy 2 using standard PostgreSQL connections.

### 2. Session Pooler vs. Direct Connection
- **Session Pooler (Recommended)**: Render and many cloud container hosts operate on IPv4-only networks. Supabase direct connections (`db.[PROJECT_REF].supabase.co:5432`) resolve to IPv6, which can cause connection timeouts on Render.
- Connecting via the Supabase **Session Pooler** (`aws-0-[REGION].pooler.supabase.com:5432` or port `6543`) resolves over IPv4 and provides connection pooling.
- **`prepare_threshold: None` Requirement**: When using connection poolers like PgBouncer in session mode, prepared statements can collide across pooled connections. In `apps/api/app/database.py`, the engine explicitly sets:
  ```python
  connect_args={"prepare_threshold": None}
  ```
  This instructs `psycopg` to avoid server-side prepared statements, ensuring clean query execution across pooled connections.

### 3. Row Level Security (RLS) Policy
- All tables created in the `public` schema must have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`).
- The application connects using the database owner credentials and enforces tenant/user access control programmatically in application logic.
- An automated test (`apps/api/tests/test_rls.py`) queries the `pg_class` catalog to verify that no table in `public` exists with `relrowsecurity = false`.

### 4. 7-Day Inactivity Pause & Keepalive
- Free-tier Supabase projects are automatically paused after 7 days of inactivity.
- A GitHub Actions workflow (`.github/workflows/keepalive.yml`) runs on a scheduled cron every 3 days (`0 0 */3 * *`).
- The workflow pings the `/health` endpoint of the deployed API (`API_HEALTH_URL`). Because `/health` executes `SELECT 1` against PostgreSQL, this keepalive ping maintains both the Render free-tier container and the Supabase database instance in an active state.

### 5. Authentication & In-Memory Rate Limiting
- The login endpoint enforces rate limiting (maximum 5 failed attempts per `(email, IP)` tuple within 15 minutes).
- **Per-Instance Limitation**: The rate limiter is strictly in-memory and operates per server instance. In multi-instance or auto-scaled environments, rate limit state is not shared across containers. Client IP is derived from the **last** entry of `X-Forwarded-For` (appended by the trusted reverse proxy) only in production when `TRUST_PROXY_HEADERS=true`; otherwise `request.client.host` is used. For multi-instance production environments, an external shared cache (such as Redis) or sticky sessions should be used.

### 6. CSV Upload Limits & Memory Constraints on Render Free Tier
- **Default Limit (`MAX_CSV_ROWS`)**: The default upload limit is set to 1,000 rows per CSV. On Render's free instance (512 MB RAM limit), limiting uploads to 1,000 candidates ensures peak memory usage stays well within the 450 MB safe target (~397 MB observed with batch size 16) and prevents Out-Of-Memory (OOM) termination.
- **Configurable Override**: The limit can be customized via the `MAX_CSV_ROWS` environment variable up to a hard-coded ceiling of 5,000 rows.

### 7. Evidence Verification System (Milestone 3A)
- **What is Collected**:
  - **GitHub GraphQL**: Compact profile metadata (`createdAt`, `followers_count`, `public_repos_count`), non-fork repository statistics (total stars, forks, language histogram, presence of README), commit/PR/review contribution counts, and external merged pull requests count (`author:LOGIN is:pr is:merged -user:LOGIN`). Personal identifiable information (emails, names, locations, bios, avatar URLs) and raw response dumps are strictly excluded.
  - **LeetCode GraphQL**: Problem-solving counts by difficulty (`easy`, `medium`, `hard`, `total`), global ranking, acceptance rate, and contribution points.
- **Limits & Time Budget**:
  - Evidence collection is scoped to the top-ranked candidates (`EVIDENCE_TOP_N=50`) following hybrid retrieval.
  - GitHub queries run with managed concurrency (`EVIDENCE_CONCURRENCY=5`), while LeetCode runs sequentially at a maximum of 1 request per second.
  - The pipeline operates under an overall time budget (`EVIDENCE_TIME_BUDGET_SECONDS=90`). Candidates remaining after the deadline expires are marked with `status="unverified"` and `reason="budget_exceeded"`.
- **TTL Cache**:
  - Evidence is cached in PostgreSQL with an indexed lookup on `(source, username, fetched_at)`.
  - Reusable evidence with status `verified` or `unverified` with reason `not_found` younger than `EVIDENCE_TTL_DAYS=7` is reused across jobs and candidates.
  - Transient errors (`status="error"`) and rate-limited runs are never cached.
- **Unofficial LeetCode Endpoint & Cloudflare**:
  - LeetCode does not provide an official public API; requests target the unofficial public GraphQL endpoint (`https://leetcode.com/graphql`).
  - Cloudflare bot protection frequently blocks or challenges traffic originating from datacenter IP ranges (such as Render or AWS) with HTTP 403.
  - Failures and timeouts (10s limit, max 1 retry) are treated as expected, recorded with `status="error"`, and **never abort the pipeline** or penalize a candidate.
- **Missing Data is Unknown, Not Zero**:
  - Candidates with missing evidence, absent links, blocked requests, or private profiles are designated as unverified.
  - In accordance with SPEC scoring principles, lack of external evidence represents an *unknown* rather than a zero score. Unverified candidates are never penalized below their hybrid retrieval baseline.
- **No-Token Behavior**:
  - If `GITHUB_TOKEN` is not configured, GitHub evidence collection records rows with `status="unverified"` and `reason="no_token"`, allowing the platform to run gracefully in minimal deployments.

### 8. Scoring Engine, Confidence & Labels (Milestone 3B)
- **Deterministic Formula**:
  - `w = SCORING_MAX_EVIDENCE_WEIGHT * confidence` (default `SCORING_MAX_EVIDENCE_WEIGHT = 0.4`)
  - When verified evidence exists: `final_score = (1 - w) * retrieval_norm + w * evidence_score`
  - When no verified evidence exists: `evidence_score = None`, `w = 0.0`, resulting in `final_score == retrieval_norm` exactly.
- **Components & Default Weights (Re-normalized over available signals)**:
  - `external_collaboration` (weight: `0.25`): Merged external PRs to other users' repositories (cap: `20`) and pull request review contributions (cap: `50`).
  - `repo_impact` (weight: `0.15`): Log-saturated total stars (cap: `500`), forks (cap: `100`), and followers count (cap: `100`).
  - `sustained_activity` (weight: `0.25`): Annual commit volume (cap: `1500`), repository push recency (graded within 90, 180, and 365 days), and GitHub account age (cap: `1825` days / 5 years).
  - `breadth` (weight: `0.10`): Distinct programming languages in repository histogram (cap: `6`) and public repository count (cap: `30`).
  - `skill_overlap` (weight: `0.15`): Overlap ratio between technologies specified in the job description and technologies verified in candidate repos and language histograms (from an 80+ term canonical vocabulary with aliases). Excluded if job description specifies no recognizable technologies.
  - `leetcode` (weight: `0.10`): Problem-solving volume weighted by difficulty (0.45 hard, 0.40 medium, 0.15 easy) and contest rating (scaling above 1200 up to 2400).
- **Saturating Transform**:
  - All signals use log-saturating transforms: $x \to \min(1.0, \frac{\log(1 + x)}{\log(1 + \text{cap})})$. This prevents vanity metric gaming or star inflation (e.g., 1,000,000 stars provides no more advantage than the saturation cap of 500).
- **Confidence Computation ($0.0 \le \text{confidence} \le 1.0$)**:
  - 0.0 when no sources are verified.
  - GitHub verified contributes up to 0.70, scaled by data richness (sample size, account age, and activity volume).
  - LeetCode verified contributes up to 0.30, scaled by total solved problem count.
  - Sum is capped at 1.0.
- **Labels & Decision Rules**:
  - `confidence < SCORING_MIN_CONFIDENCE (0.2)` $\to$ `insufficient_evidence`
  - `final_score >= SCORING_STRONG_THRESHOLD (0.75)` $\to$ `strong_match`
  - Otherwise $\to$ `needs_review`
  - **No reject label anywhere.**
- **The No-Penalty Rule**:
  - Missing or unverified evidence is strictly treated as *unknown*, not zero. Candidates with unverified profiles, private accounts, or rate-limited runs retain their hybrid retrieval score exactly (`final_score == retrieval_norm`). They are never ranked below candidates whose verified public evidence proved weak.
- **Signals Not Yet Available (Deferred)**:
  - While `has_readme` indicates documentation presence, deep repository test presence/coverage analysis and full README quality parsing are not currently extracted from the compact GraphQL query and remain deferred.
- **Provisional Note**:
  - All weights, caps, and label thresholds are provisional and can be re-tuned via `SCORING_*` environment variables. They will be officially benchmarked and frozen against the evaluation harness in Milestone 4.

---

## Testing

The test suite supports two testing modes to balance fast developer iteration with full production fidelity:

### 1. Fast SQLite Unit Tests (Default Mode)
- **Purpose**: Rapid local feedback during development with zero infrastructure dependencies.
- **Coverage**: Endpoint validation, authentication, CSV ingestion parsing, schemas, business logic, and rate limiting.
- **Execution**: Run without setting `TEST_DATABASE_URL` (or using in-memory SQLite):
  ```bash
  cd apps/api
  python -m pytest -q -m "not postgres"
  ```
- **Constraint**: SQLite does not support native `pgvector` or PostgreSQL full-text search dictionaries (`to_tsvector`), and stores vector embeddings as JSON/lists rather than NumPy arrays.

### 2. Live PostgreSQL + pgvector Integration Tests (`@pytest.mark.postgres`)
- **Purpose**: Verifies real database migrations, Row-Level Security (RLS) enforcement on all public schema tables, native `pgvector` `<=>` cosine distance queries, PostgreSQL `tsvector` OR-query retrieval, and `numpy.ndarray` deserialization behavior.
- **Prerequisites**: Ensure the local pgvector Docker container is running (`docker compose up -d`).
- **Execution**: Provide `TEST_DATABASE_URL` pointing at the local Docker database:
  ```bash
  cd apps/api
  # PowerShell:
  $env:TEST_DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5433/verihire"
  python -m pytest -q

  # Bash:
  TEST_DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5433/verihire" python -m pytest -q
  ```
- **CI Enforcement**: Tests requiring Postgres are marked with `@pytest.mark.postgres`. In CI (where `CI=true` and `REQUIRE_POSTGRES=true`), a `pytest_runtest_makereport` hook strictly disallows skipping any `@pytest.mark.postgres` test, immediately failing the build if the database container is unreachable or any test is skipped.


