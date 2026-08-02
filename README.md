# VeriHire AI

Evidence-backed hiring intelligence — rank candidates by proven GitHub and LeetCode signals, not resume keywords.

## What it does

VeriHire runs a **3-layer AI pipeline** on your candidate pool:

1. **Semantic retrieval** — embeds resumes and matches against the job description (ChromaDB + MiniLM)
2. **Evidence verification** — validates claims via GitHub, LeetCode, and Codeforces APIs
3. **LLM reasoning** — Groq generates recruiter summaries and verdicts (HIRE / REVIEW / REJECT)

## Features

- 🎯 **AI-Powered Ranking** — 3-layer pipeline with RAG, evidence verification, and LLM reasoning
- 🔐 **Authentication** — Supabase auth with JWT tokens
- 💾 **PostgreSQL Storage** — Persistent job and candidate data with Row Level Security
- 🚀 **GPU Acceleration** — Fast embedding generation with CUDA support
- 📊 **Real-time Dashboard** — Track pipeline progress and view results
- 📤 **Export Results** — Download rankings as CSV or JSON
- 🔍 **Detailed Profiles** — View GitHub stats, LeetCode performance, and risk flags

## Recruiter workflow

1. **Sign up / Login** — Create an account or sign in
2. **Upload a CSV** with your candidate pool (or use the built-in sample dataset)
3. **Paste a job description**
4. Click **Analyze Candidates** — pipeline runs in background
5. Review rankings, filter by verdict, export results, drill into candidate profiles

### CSV format

| Column | Required | Notes |
|--------|----------|-------|
| `role` | Yes | Job title / target role |
| `name` | No | Candidate name |
| `email` | No | Contact email |
| `skills` | No | Pipe- or comma-separated skills |
| `online_links` | No | GitHub / LeetCode URLs |
| `positions` | No | Work history (JSON or text) |
| `responsibilities` | No | Role responsibilities |

Max file size: **50 MB**. Example:

```csv
name,email,role,skills,online_links
Jane Doe,jane@co.com,Backend Engineer,Python|FastAPI,https://github.com/jane
```

## Project structure

```
├── backend/          FastAPI · ChromaDB · Groq · PostgreSQL
│   ├── app/          API routes, 3-layer pipeline, parsers
│   ├── data/         Sample CSV, ChromaDB persistence
│   ├── database/     PostgreSQL schema and migrations
│   └── tests/        Unit and integration tests
├── frontend/         React · TypeScript · Vite · Tailwind · Framer Motion
│   ├── src/pages/    Landing, Dashboard, CandidateDetail, Auth
│   └── src/data/     Mock data for development
└── docs/             Project documentation and diagrams
```

## Tech stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Framer Motion, Lucide |
| Backend | FastAPI, ChromaDB, sentence-transformers, Groq, pandas, Supabase |
| Database | PostgreSQL (Supabase) with Row Level Security |
| Auth | Supabase Authentication with JWT |
| AI/ML | sentence-transformers (MiniLM), Groq (Llama 3.3 70B), spaCy |

## Local development

### Prerequisites

- Python 3.10+
- Node.js 18+
- CUDA-capable GPU (optional, for faster embeddings)
- Supabase account (for auth and database)

### Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# Edit .env and add:
# - GROQ_API_KEY (from https://console.groq.com)
# - GITHUB_TOKEN (GitHub Personal Access Token)
# - SUPABASE_URL (from Supabase project settings)
# - SUPABASE_ANON_KEY (from Supabase project settings)
# - SUPABASE_SERVICE_ROLE_KEY (from Supabase project settings)
# - JWT_SECRET (from Supabase project settings → API → JWT Secret)

# Run database migrations
# 1. Go to Supabase SQL Editor
# 2. Run backend/database/schema.sql
# 3. Run backend/database/fix_rls.sql

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/api/health  
API docs: http://localhost:8000/docs

### Frontend setup

```bash
cd frontend
npm install

# Copy and configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux

# Edit .env and set:
# VITE_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

App: http://localhost:5173

## API endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signup` | Create new account |
| `POST` | `/api/auth/login` | Sign in |
| `GET` | `/api/auth/me` | Get current user |
| `POST` | `/api/auth/logout` | Sign out |

### Ranking Pipeline

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/rank` | Start ranking pipeline (requires auth) |
| `GET` | `/api/rank/{job_id}/status` | Pipeline job status |

### Candidates

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/candidates` | List ranked candidates (requires auth) |
| `GET` | `/api/candidates/{id}` | Candidate detail |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health |
| `GET` | `/api/stats` | Dashboard statistics (requires auth) |
| `GET` | `/api/export` | Export results (CSV / JSON, requires auth) |

## Database setup

### Supabase configuration

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run:
   - `backend/database/schema.sql` — creates tables and RLS policies
   - `backend/database/fix_rls.sql` — updates policies for service role bypass
3. Get credentials from **Project Settings → API**:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_ANON_KEY`
   - service_role key → `SUPABASE_SERVICE_ROLE_KEY`
   - JWT Secret → `JWT_SECRET`

### Database schema

- **jobs** — Stores ranking job submissions (job_id, user_id, job_description)
- **candidates** — Stores ranked candidates with enrichments (rank, scores, verdict, GitHub evidence, etc.)

Row Level Security (RLS) ensures users can only access their own data.

## Environment variables

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for Layer 3 LLM | Yes |
| `GITHUB_TOKEN` | GitHub PAT for evidence verification | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anon/public key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `JWT_SECRET` | Supabase JWT secret | Yes |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | No |
| `CHROMADB_PATH` | ChromaDB persistence directory | No |
| `AUTH_ENABLED` | Enable/disable authentication (default: true) | No |

### Frontend (`frontend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_API_URL` | Backend base URL (no trailing slash) | Yes |

## GPU acceleration

The backend automatically detects and uses CUDA-capable GPUs for embedding generation:

- **With GPU**: ~22 seconds for 100 candidates
- **Without GPU**: ~725 seconds for 100 candidates

To enable GPU support:
1. Install CUDA toolkit (11.8 or 12.x)
2. Install PyTorch with CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu118`

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing — storytelling scroll, hero video, stats |
| `/login` | Sign in page |
| `/signup` | Create account page |
| `/dashboard` | Recruiter dashboard — CSV upload, JD input, rankings |
| `/candidate/:id` | Candidate detail — skills, GitHub, LeetCode, risk flags |

## Documentation

Full project overview with architecture diagrams and API reference:

- **[docs/VeriHire-Project-Overview.pdf](docs/VeriHire-Project-Overview.pdf)** — 9-page PDF with flow diagrams
- [docs/VeriHire-Project-Overview.html](docs/VeriHire-Project-Overview.html) — HTML source

## License

MIT · [Narayan1006/VireHire](https://github.com/Narayan1006/VireHire)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
