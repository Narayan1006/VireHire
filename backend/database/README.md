# VireHire AI - Database Migration

## 📋 Overview

This directory contains the database schema and migration tools for moving from JSON file storage (`candidates.json`) to Supabase PostgreSQL.

---

## 📁 Files

| File | Description |
|------|-------------|
| `schema.sql` | Complete PostgreSQL schema with tables, indexes, RLS policies, and helper functions |
| `MIGRATION_GUIDE.md` | Step-by-step migration instructions |
| `migrate_json_to_pg.py` | Python script to migrate existing `candidates.json` data to PostgreSQL |
| `README.md` | This file |

---

## 🗄️ Database Schema

### Tables

#### `public.jobs`
Stores ranking job submissions. Each job belongs to a user.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `job_id` | TEXT | 8-char hex ID from frontend (unique) |
| `user_id` | UUID | References `auth.users(id)` |
| `job_description` | TEXT | Job description text |
| `created_at` | TIMESTAMPTZ | Job creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

**Indexes:**
- `idx_jobs_user_id` on `user_id`
- `idx_jobs_job_id` on `job_id`
- `idx_jobs_created_at` on `created_at DESC`

---

#### `public.candidates`
Stores ranked candidates with all enrichments from the 3-layer pipeline.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `job_id` | TEXT | References `jobs(job_id)` |
| `candidate_id` | TEXT | Candidate ID from CSV |
| `name` | TEXT | Candidate name |
| `email` | TEXT | Candidate email |
| `role` | TEXT | Job role |
| `rank` | INTEGER | Sequential rank (1 = best) |
| `percentile` | INTEGER | Percentile score (0-100) |
| `pr_score` | INTEGER | Overall PR score (0-100) |
| `github_score` | INTEGER | GitHub score (0-100) |
| `dsa_score` | INTEGER | DSA score (0-100) |
| `verdict` | TEXT | HIRE, REVIEW, or REJECT |
| `skills` | JSONB | Array of SkillConfidence objects |
| `github_evidence` | JSONB | GitHub verification data |
| `leetcode` | JSONB | LeetCode stats |
| `codeforces` | JSONB | Codeforces stats (nullable) |
| `timeline` | JSONB | Array of TimelineEntry objects |
| `risk_flags` | JSONB | Array of RiskFlag objects |
| `summary` | TEXT | LLM-generated explanation |
| `layer1_score` | DOUBLE PRECISION | Semantic similarity (0.0-1.0) |
| `layer2_score` | DOUBLE PRECISION | Evidence verification (0.0-1.0) |
| `layer3_confidence` | DOUBLE PRECISION | LLM confidence (0.0-1.0) |
| `created_at` | TIMESTAMPTZ | Candidate creation timestamp |

**Indexes:**
- `idx_candidates_job_id` on `job_id`
- `idx_candidates_rank` on `(job_id, rank)`
- `idx_candidates_verdict` on `(job_id, verdict)`
- `idx_candidates_pr_score` on `(job_id, pr_score DESC)`
- `idx_candidates_skills` (GIN) on `skills`
- `idx_candidates_github_evidence` (GIN) on `github_evidence`

**Constraints:**
- Unique: `(job_id, candidate_id)`
- Check: `rank >= 1`
- Check: `percentile BETWEEN 0 AND 100`
- Check: `pr_score BETWEEN 0 AND 100`
- Check: `verdict IN ('HIRE', 'REVIEW', 'REJECT')`

---

## 🔒 Row Level Security (RLS)

### Jobs Table Policies

| Policy | Operation | Rule |
|--------|-----------|------|
| Users can view their own jobs | SELECT | `auth.uid() = user_id` |
| Users can insert their own jobs | INSERT | `auth.uid() = user_id` |
| Users can update their own jobs | UPDATE | `auth.uid() = user_id` |
| Users can delete their own jobs | DELETE | `auth.uid() = user_id` |

### Candidates Table Policies

| Policy | Operation | Rule |
|--------|-----------|------|
| Users can view candidates from their jobs | SELECT | Job belongs to user |
| Users can insert candidates to their jobs | INSERT | Job belongs to user |
| Users can update candidates in their jobs | UPDATE | Job belongs to user |
| Users can delete candidates from their jobs | DELETE | Job belongs to user |

**Security Guarantee:** Users can ONLY access jobs and candidates they own. No cross-user data leakage.

---

## 🔧 Helper Functions

### `get_job_with_stats(p_job_id TEXT)`
Returns job details with candidate statistics:
- `candidate_count`: Total candidates
- `hire_count`: Candidates with HIRE verdict
- `review_count`: Candidates with REVIEW verdict
- `reject_count`: Candidates with REJECT verdict

### `delete_expired_jobs()`
Deletes jobs older than 90 days (retention policy).
Returns count of deleted jobs.

---

## 🚀 Quick Start

### 1. Run Schema in Supabase

```sql
-- Copy contents of schema.sql and run in Supabase SQL Editor
```

### 2. Install Dependencies

```bash
pip install psycopg2-binary asyncpg
```

### 3. Update Backend

```python
# In app/main.py
from app.storage.candidate_store_pg import CandidateStorePG as CandidateStore
```

### 4. Restart Backend

```bash
uvicorn app.main:app --reload
```

---

## 📊 Data Migration

### Migrate Existing Data

```bash
python database/migrate_json_to_pg.py
```

**What it does:**
1. Reads `data/candidates.json`
2. Creates jobs in Supabase (assigned to your user)
3. Creates candidates for each job
4. Preserves timestamps

**Requirements:**
- User ID (UUID) from Supabase auth
- Supabase credentials in `.env`
- Tables created (run `schema.sql` first)

---

## ✅ Verification

After migration, verify:

```sql
-- Check jobs
SELECT job_id, user_id, created_at FROM public.jobs;

-- Check candidates
SELECT job_id, candidate_id, name, rank, verdict 
FROM public.candidates 
ORDER BY job_id, rank 
LIMIT 10;

-- Check RLS policies
SELECT tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';
```

---

## 🔄 API Compatibility

The PostgreSQL store maintains **100% API compatibility** with the JSON store:

| Method | JSON Store | PostgreSQL Store | Compatible |
|--------|------------|------------------|------------|
| `save_candidates()` | ✅ | ✅ | ✅ |
| `load_candidates()` | ✅ | ✅ | ✅ |
| `get_job_ids()` | ✅ | ✅ | ✅ |
| `get_candidate()` | ✅ | ✅ | ✅ |
| `get_latest_job_id()` | ✅ | ✅ | ✅ |
| `delete_job()` | ✅ | ✅ | ✅ |
| `enforce_retention()` | ✅ | ✅ | ✅ |

**No changes required** to:
- Layer 1 (RAG)
- Layer 2 (Evidence)
- Layer 3 (LLM)
- Ranking formulas
- API endpoints
- Frontend

---

## 🎯 Benefits

| Feature | JSON File | PostgreSQL |
|---------|-----------|------------|
| Multi-user support | ❌ | ✅ |
| Row-level security | ❌ | ✅ |
| Scalability | Limited | High |
| Query performance | Slow | Fast (indexed) |
| Data integrity | None | Foreign keys, constraints |
| Backup & recovery | Manual | Automatic |
| Production-ready | ❌ | ✅ |

---

## 📝 Notes

- **Backward Compatibility**: The old JSON store (`candidate_store.py`) remains available for rollback
- **Zero Downtime**: Migration can be done without stopping the service
- **Data Preservation**: All existing data can be migrated with timestamps intact
- **Security First**: RLS ensures users can only access their own data

---

## 🆘 Support

For issues or questions:
1. Check `MIGRATION_GUIDE.md` for detailed instructions
2. Review Supabase logs: Dashboard → Logs → Postgres Logs
3. Verify RLS policies are active
4. Test with Supabase SQL Editor first

---

## 📚 References

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
