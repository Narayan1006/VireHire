# VeriHire v2

> **Evidence-backed hiring intelligence platform.** VeriHire ranks technical job candidates by verifiable public proof of work—such as GitHub contributions, external pull requests, repository quality, and LeetCode problem-solving stats—rather than self-reported resume claims or keyword matching.

[![CI](https://github.com/singh-naman1/VireHire-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/singh-naman1/VireHire-v2/actions/workflows/ci.yml)
[![Keepalive Ping](https://github.com/singh-naman1/VireHire-v2/actions/workflows/keepalive.yml/badge.svg)](https://github.com/singh-naman1/VireHire-v2/actions/workflows/keepalive.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Pitch

Traditional hiring platforms rank candidates by keyword density, buzzword matching, and unverified resume claims. This incentives keyword-stuffed resumes and disadvantages engineers whose skills are demonstrated in code rather than buzzwords.

**VeriHire inverts this paradigm:**
1. **Verifiable Proof Over Self-Reported Text**: Real GitHub contributions, external merged pull requests to other organizations, repository impact, commit recency, and verified LeetCode problem-solving metrics.
2. **Missing Evidence is Unknown, Not Zero**: Candidates without public profiles or with private corporate repositories are **never penalized** below their semantic retrieval baseline (`final_score == retrieval_norm`).
3. **Calibrated Deterministic Scoring**: No black-box score calculations. All score components use log-saturating transforms to prevent vanity metric gaming, with strict confidence weighting.
4. **Explainable AI Guardrails**: Groq LLM generates structured, audit-ready explanations grounded strictly in verified stored evidence. The LLM **never** decides or reorders candidate rankings.
5. **Human-in-the-Loop Decision Support**: VeriHire produces recommendations (`strong_match`, `needs_review`, `insufficient_evidence`)—there is **no reject label**. Humans always make hiring decisions.

---

## Architecture

VeriHire is designed as a modular, resource-efficient architecture adhering to strict token safety, Row-Level Security, and session-pooled PostgreSQL with pgvector.

```mermaid
flowchart TD
    subgraph Client["Frontend (Vercel)"]
        UI["React 19 + Vite + TypeScript<br/>Tailwind CSS + shadcn/ui"]
    end

    subgraph Service["Backend API (Render: verihire-api-v2)"]
        FastAPI["FastAPI 0.115 (Python 3.12)<br/>Uvicorn + Pydantic v2"]
        EmbedEngine["FastEmbed ONNX<br/>BAAI/bge-small-en-v1.5 (384d)"]
        ScoreEngine["Deterministic Scoring Engine<br/>Log-Saturating Transforms"]
        LLMService["Groq LLM Service<br/>llama-3.3-70b-versatile (JSON Mode)"]
    end

    subgraph Storage["Database (Supabase Session Pooler)"]
        PG[("PostgreSQL 16 + pgvector<br/>Row Level Security (RLS) on all tables")]
        TSVector[("Postgres Full-Text Search<br/>tsvector OR Queries")]
        VectorStore[("pgvector Cosine Distance<br/>vector(384)")]
        TTLCache[("Evidence TTL Cache<br/>7-Day Invalidation")]
    end

    subgraph External["External Proof Sources"]
        GH["GitHub GraphQL API<br/>Contributions, PRs, Star Sinks"]
        LC["LeetCode Public GraphQL<br/>Best-Effort Problem Stats"]
    end

    subgraph Automation["Operations & CI"]
        CI["GitHub Actions CI<br/>Ruff + Pytest (Live PG) + Web Build"]
        Keepalive["GitHub Actions Keepalive<br/>Scheduled /health Ping (Every 3 Days)"]
    end

    UI -->|"HTTPS + JWT Access Token"| FastAPI
    FastAPI -->|"CSV Parse & Batch Embed"| EmbedEngine
    EmbedEngine -->|"Persist Embeddings & tsvector"| PG
    FastAPI -->|"Hybrid RRF Search"| TSVector
    FastAPI -->|"Vector Similarity (<=>)"| VectorStore
    FastAPI -->|"Verify Profiles (Async + Budget)"| GH
    FastAPI -->|"Verify Stats (Best-Effort)"| LC
    GH & LC -->|"Cache Verified Payloads"| TTLCache
    FastAPI -->|"Compute Calibrated Confidence & Scores"| ScoreEngine
    ScoreEngine -->|"Persist Rankings"| PG
    FastAPI -->|"Generate Structured Audit Summaries"| LLMService
    LLMService -->|"Explainable JSON (Zero Re-ranking)"| UI
    Keepalive -->|"Pings /health (SELECT 1)"| FastAPI
    FastAPI -->|"Pooled Connection (prepare_threshold: None)"| PG
```

### End-to-End Pipeline
1. **Ingest**: Recruiter uploads a candidate CSV. The API validates rows, computes 384-dimensional dense embeddings using local ONNX `FastEmbed`, generates PostgreSQL search `tsvector`s, and persists candidate records.
2. **Hybrid Retrieve**: PostgreSQL executes reciprocal rank fusion (RRF, $k=60$) combining full-text lexical search and vector cosine similarity to retrieve candidate matches without external vector databases.
3. **Verify Evidence**: Top candidates enter an async evidence pipeline querying GitHub GraphQL and LeetCode endpoints within an overall time budget (`EVIDENCE_TIME_BUDGET_SECONDS=90`). Results are cached in PostgreSQL with a 7-day TTL.
4. **Deterministic Score**: Verified signals (external PRs, repository impact, commit recency, tech vocabulary overlap, contest ratings) are aggregated using log-saturating transforms and scaled by data confidence.
5. **Structured Explanation**: Groq LLM analyzes stored evidence against the job description to produce executive summaries, strengths, gaps, and rationale in strict JSON format.

---

## Evaluation & Benchmark Results

VeriHire includes a standalone, reproducible evaluation harness located in `eval/` with ground-truth graded candidates (Grade 0: irrelevant to Grade 3: expert verified match) across diverse software engineering domains.

### Benchmark Comparison

The table below reflects real, reproducible benchmark measurements from [`eval/results.json`](eval/results.json):

| Retrieval & Scoring Strategy | NDCG@10 | Precision@10 | MRR | Mean Latency | LLM Calls / Run | Description |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **1. Keyword / BM25** | **0.9852** | 0.2667 | 1.0000 | 0.34 ms | 0 | Pure lexical matching on candidate resume and links |
| **2. Dense Embeddings Only** | 0.9223 | 0.2667 | 1.0000 | 15.28 ms | 0 | Semantic cosine distance via `BAAI/bge-small-en-v1.5` |
| **3. Hybrid Retrieval (RRF)** | 0.9783 | 0.2667 | 1.0000 | 14.66 ms | 0 | Reciprocal Rank Fusion ($k=60$) combining BM25 and dense embeddings |
| **4. Full Pipeline (Hybrid + Evidence)** | 0.9666 | 0.2667 | 1.0000 | 21.06 ms | 12 | Hybrid RRF + verified GitHub/LeetCode signals + confidence-weighting |

> [!NOTE]
> **Key Finding**: While lexical search excels at direct keyword presence, Hybrid RRF robustly handles semantic paraphrasing without losing exact skill terms. The Full Pipeline introduces objective, hard-to-fake public evidence: verified high-impact candidates receive confidence-weighted score promotions, while candidates without public proof preserve their retrieval baseline without penalty.

### Calibrated Thresholds (Frozen in Milestone 4)

Thresholds and weights were systematically calibrated against evaluation ground-truth distributions and frozen:

| Parameter | Calibrated Value | Rationale |
|---|:---:|---|
| `SCORING_STRONG_THRESHOLD` | **0.75** | Aligns with empirical separation: Grade 3 (Expert) mean score = `0.842` vs Grade 2 (Good) mean score = `0.724`. |
| `SCORING_MIN_CONFIDENCE` | **0.20** | Ensures unverified candidates or profiles with minimal data stay designated as `insufficient_evidence` rather than receiving an unsubstantiated rating. |
| `SCORING_MAX_EVIDENCE_WEIGHT` | **0.40** | Restricts the maximum evidence swing ($w \le 0.40$) so semantic resume qualifications remain the foundational baseline ($60\%+$). |

### Reproducing the Evaluation
To run the evaluation benchmark suite locally and reproduce the results table:
```bash
# Ensure local postgres container is running or run purely in-memory
cd apps/api
.venv\Scripts\python -m eval.run_eval  # Windows
# or:
python -m eval.run_eval                # Linux/macOS
```
The output updates [`eval/results.json`](eval/results.json) directly.

---

## Limitations and Fairness

Automated recruitment tools carry severe ethical and legal risks if misapplied. VeriHire was architected from inception around algorithmic fairness, anti-bias principles, and strict human agency.

### 1. The No-Penalty Rule: Missing Evidence is Unknown, Not Zero
- Many candidates do not have active public GitHub profiles or public LeetCode accounts. Reasons include:
  - Employment under strict corporate NDAs or proprietary closed-source codebases.
  - Work in sectors like banking, enterprise ERP, defense, or infrastructure where open-source contribution is prohibited.
  - Personal responsibilities, family caregiving, or lack of unpaid leisure time to contribute to open source.
- **VeriHire Rule**: When no verified evidence exists, evidence weight is zero ($w = 0$), and `final_score` equals `retrieval_norm` exactly.
- Unverified candidates receive the status label `insufficient_evidence`. They are **never** assigned a zero score, never down-ranked below their retrieval baseline, and never discarded.

### 2. Demographic and Open-Source Equity
- Studies demonstrate that public open-source participation is unevenly distributed across demographic groups. Treating GitHub stars or commit streaks as mandatory criteria introduces systemic bias.
- In VeriHire, public proof acts solely as an **additive validation boost** for claims made on a resume. Lack of public proof merely indicates that external verification was unavailable, prompting a standard recruiter resume review.

### 3. Log-Saturating Transforms Against Vanity Metric Gaming
- Raw metrics like GitHub stars, followers, and commit counts are vulnerable to manipulation (e.g., star trading networks, automated green-square bots, fork-bombing).
- VeriHire applies a logarithmic saturation function to all signals:
  $$\text{score}(x) = \min\left(1.0, \frac{\ln(1 + x)}{\ln(1 + \text{cap})}\right)$$
- Hard caps prevent vanity gaming:
  - GitHub Stars: saturated at 500 stars.
  - Commit volume: saturated at 1,500 annual commits.
  - Account age: capped at 5 years.
  - Merged external PRs to other users' repositories and code review contributions are weighted substantially higher than self-owned repository commits.

### 4. Decision Support, Never Automated Decisions
- **No Reject Label**: VeriHire supports three recommendation labels: `strong_match`, `needs_review`, and `insufficient_evidence`. There is no "reject" or "unqualified" designation.
- The platform is strictly an assistive decision-support tool. Final evaluation, interview selection, and hiring decisions must be performed by human hiring managers.

### 5. LLM Guardrails & Anti-Hallucination
- The Groq LLM (`llama-3.3-70b-versatile`) is strictly restricted to generating textual explanations from pre-verified, stored JSON evidence.
- The LLM **never** calculates scores, modifies scores, or changes candidate rank ordering.
- If the LLM call times out, fails, or violates JSON validation, the system falls back to a deterministic, template-based explanation without disruption.

---

## Core Technologies

| Layer | Technology | Version | Hosting / Provider |
|---|---|---|---|
| **Frontend UI** | React, Vite, TypeScript, Tailwind CSS, shadcn/ui | React 19, Vite 6 | [Vercel](https://vercel.com) |
| **Backend API** | FastAPI, Uvicorn, Pydantic, SQLAlchemy 2 | Python 3.12, FastAPI 0.115 | [Render](https://render.com) (`verihire-api-v2`) |
| **Database** | PostgreSQL with `pgvector` & Row-Level Security | PostgreSQL 16 | [Supabase](https://supabase.com) (Session Pooler) |
| **Embeddings** | FastEmbed (`BAAI/bge-small-en-v1.5`, 384 dims) | FastEmbed ONNX | Local CPU runtime |
| **LLM Reasoning**| Groq API (`llama-3.3-70b-versatile`, JSON Mode) | Groq SDK / HTTPX | [Groq](https://groq.com) |
| **Evidence APIs** | GitHub GraphQL API, LeetCode Public GraphQL | v4 GraphQL | GitHub / LeetCode |
| **CI / Keepalive**| GitHub Actions (Pytest, Ruff, npm build, cron) | Actions v4 | GitHub |

---

## Local Development Quickstart

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+ and npm

### 1. Start Local PostgreSQL with `pgvector`
```bash
docker compose up -d
```
*Runs PostgreSQL 16 with `pgvector` on `localhost:5433` (mapped from container port 5432).*

### 2. Set Up Backend API (`apps/api`)
```bash
cd apps/api

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies and pre-download embedding model
pip install -r requirements.txt
python scripts/download_model.py
```

### 3. Configure Local Environment
Create `apps/api/.env`:
```ini
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5433/verihire
JWT_SECRET=your-local-development-jwt-secret-min-32-chars
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
ENV=development

# Optional: Add for live verification and AI explanations
GITHUB_TOKEN=your_personal_github_token_optional
GROQ_API_KEY=your_groq_api_key_optional
```

### 4. Run Migrations & Start API Server
```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*API is accessible at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.*

### 5. Set Up and Run Frontend (`apps/web`)
```bash
cd ../web
npm install

# Create apps/web/.env
echo "VITE_API_URL=http://localhost:8000" > .env

# Start Vite dev server
npm run dev
```
*Open `http://localhost:5173` to interact with VeriHire.*

---

## Production Deployment Guide

### Backend Deployment (Render)
The backend is deployed as a Web Service on Render (`verihire-api-v2`):
- **Runtime**: Python 3.12
- **Root Directory**: `apps/api`
- **Build Command**: `pip install -r requirements.txt && python scripts/download_model.py`
- **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`

#### Required Environment Variables in Render:
| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase **Session Pooler** connection string (`postgresql+psycopg://...aws-0-[region].pooler.supabase.com:5432/...`) |
| `JWT_SECRET` | 32+ character cryptographic secret for signing access tokens |
| `CORS_ORIGINS` | Your deployed Vercel domain (e.g., `https://verihire-web.vercel.app`) |
| `ENV` | `production` |
| `GITHUB_TOKEN` | GitHub personal access token (fine-grained, read-only public repo scope) |
| `GROQ_API_KEY` | Groq API key for structured explanation generation |

> [!IMPORTANT]
> **Database Pooler Note**: Always connect via the Supabase **Session Pooler** (IPv4). The SQLAlchemy engine explicitly sets `connect_args={"prepare_threshold": None}` to disable server-side prepared statements on pooled connections.

### Frontend Deployment (Vercel)
The web application is deployed via Vercel:
- **Root Directory**: `apps/web`
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variable**: `VITE_API_URL` pointing to your Render backend (e.g., `https://verihire-api-v2.onrender.com`).
- The repository includes [`apps/web/vercel.json`](apps/web/vercel.json) for automatic single-page application (SPA) rewrites to `/index.html`.

---

## Operations & Monitoring

### 1. Scheduled Keepalive Ping
Free-tier Supabase projects automatically pause after 7 days of inactivity, and free-tier Render instances sleep after 15 minutes of idle time.
- VeriHire includes an automated GitHub Actions keepalive workflow ([`.github/workflows/keepalive.yml`](.github/workflows/keepalive.yml)).
- Runs every 3 days at 00:00 UTC (`0 0 */3 * *`).
- Executes `curl -fsS "$API_HEALTH_URL"` against `/health`.
- Because `/health` executes `SELECT 1` on PostgreSQL, both the API instance and the Supabase database stay active.

### 2. Error Monitoring via Structured Logs
- Application errors and unhandled exceptions are intercepted by a centralized exception handler in [`apps/api/app/main.py`](apps/api/app/main.py).
- Unhandled errors are logged with HTTP method, request path, error details, and stack traces via standard Python structured logging (`verihire.api`), while returning clean HTTP 500 JSON responses to the client without leaking sensitive system details.
- Request validation errors sanitize error messages to strictly prevent echoing password fields in client responses.

### 3. In-Memory Security Rate Limiting
- The authentication endpoint enforces rate limiting against credential-stuffing (5 failed attempts per `(email, IP)` tuple per 15 minutes).
- In production, when `TRUST_PROXY_HEADERS=true`, client IP is resolved from the trusted reverse proxy header.

---

## Testing & Quality Assurance

VeriHire enforces strict test suites covering fast SQLite unit tests, PostgreSQL integration tests, and frontend production builds:

```bash
# Fast unit tests (SQLite / In-Memory):
cd apps/api
.venv\Scripts\python -m pytest -q -m "not postgres"

# Full suite with PostgreSQL + pgvector + RLS enforcement:
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5433/verihire"
.venv\Scripts\python -m pytest -v

# Run code style and lint checks:
.venv\Scripts\python -m ruff check app tests ../../eval

# Test frontend build:
cd ../web
npm run build
```

---

## License

This project is licensed under the [MIT License](LICENSE).
