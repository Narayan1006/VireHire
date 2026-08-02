# VeriHire AI - Backend

AI-native hiring intelligence platform with a 3-layer candidate ranking pipeline.

## Architecture

```
CSV Data → Layer 1 (Semantic Retrieval) → Layer 2 (Evidence Verification) → Layer 3 (LLM Reasoning) → Ranking + Verdicts
```

### Layer 1: Semantic Retrieval
- Parses CSV → chunks resumes → generates embeddings (all-MiniLM-L6-v2)
- Stores in ChromaDB → retrieves top-K by cosine similarity to job description

### Layer 2: Evidence Verification
- Extracts evidence from GitHub, LeetCode, Codeforces APIs (parallel)
- Calculates deterministic scores: GitHub (0-100), DSA (0-100), Consistency (0-1)
- Generates risk flags for skill gaps

### Layer 3: LLM Reasoning
- Generates 100-300 word hiring summaries via Groq API (Llama 3.3 70B)
- Evidence-only prompts to prevent hallucination
- Template fallback on API failure

### Ranking Engine
- PR Score: `GitHub*0.4 + DSA*0.4 + Consistency*100*0.2`
- Final Score: `L1*0.2 + L2*0.6 + L3*0.2`
- Verdicts: `PR≥80 → HIRE, PR≥60 → REVIEW, PR<60 → REJECT`

## Setup

### Prerequisites
- Python 3.11+
- Groq API key
- GitHub Personal Access Token (optional, increases rate limits)

### Installation

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
GROQ_API_KEY=gsk_your_key_here
GITHUB_TOKEN=github_pat_your_token_here
CHROMADB_PATH=./data/chroma_db
CSV_DATA_PATH=./data/resume_data.csv
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Running

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root info |
| `POST` | `/api/rank` | Trigger ranking pipeline |
| `GET` | `/api/rank/{job_id}/status` | Check pipeline status |
| `GET` | `/api/candidates` | List ranked candidates (filterable) |
| `GET` | `/api/candidates/{id}` | Get candidate detail |
| `GET` | `/api/export` | Export as CSV or JSON |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/health` | System health check |

### POST /api/rank

```json
{
  "job_description": "We need a Senior Full-Stack Engineer with React...",
  "csv_file_path": "./data/resume_data.csv",
  "top_k": 200,
  "llm_top_k": 50
}
```

### GET /api/candidates

Query parameters: `job_id`, `verdict`, `min_score`, `limit`, `offset`

### GET /api/export

Query parameters: `job_id`, `verdict`, `format` (csv/json)

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/          # FastAPI route handlers
│   │   ├── error_handlers.py
│   │   ├── rate_limiter.py
│   │   └── logging_middleware.py
│   ├── embeddings/
│   │   └── embedder.py      # Sentence-transformer embeddings
│   ├── integrations/
│   │   ├── github_client.py  # GitHub REST API
│   │   ├── leetcode_client.py # LeetCode GraphQL
│   │   ├── codeforces_client.py # Codeforces REST
│   │   └── groq_client.py   # Groq LLM API
│   ├── models/
│   │   ├── candidate.py     # Core data models
│   │   ├── evidence.py      # GitHub/LC/CF evidence models
│   │   ├── ranking.py       # Pipeline intermediate models
│   │   └── api_schemas.py   # Request/response schemas
│   ├── parsers/
│   │   ├── csv_parser.py    # CSV ingestion
│   │   └── resume_parser.py # Resume text chunking
│   ├── services/
│   │   ├── layer1_rag.py    # Semantic retrieval
│   │   ├── layer2_evidence.py # Evidence extraction + scoring
│   │   ├── layer3_llm.py    # LLM reasoning
│   │   ├── ranking_engine.py # Score aggregation + verdicts
│   │   └── orchestrator.py  # Pipeline orchestrator
│   ├── storage/
│   │   ├── vector_store.py  # ChromaDB wrapper
│   │   └── candidate_store.py # JSON persistence
│   ├── utils/
│   │   ├── logger.py        # Structured logging
│   │   ├── cache.py         # In-memory TTL cache
│   │   ├── validators.py    # Input validation
│   │   └── security.py      # Sanitization utilities
│   ├── config.py            # Settings management
│   └── main.py              # FastAPI entry point
├── data/
│   └── test_candidates.csv
├── .env
└── requirements.txt
```

## Testing

```bash
# Run the server
uvicorn app.main:app --reload

# Trigger a pipeline
curl -X POST http://localhost:8000/api/rank \
  -H "Content-Type: application/json" \
  -d '{"job_description": "Senior React Engineer...", "csv_file_path": "./data/test_candidates.csv"}'

# Check status
curl http://localhost:8000/api/rank/{job_id}/status

# Get results
curl http://localhost:8000/api/candidates?job_id={job_id}
```

## License

Proprietary - VeriHire AI
