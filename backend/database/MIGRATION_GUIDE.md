# Database Migration Guide: JSON → Supabase PostgreSQL

## Overview

This guide walks you through migrating candidate/job persistence from `candidates.json` to Supabase PostgreSQL.

---

## Step 1: Run SQL Schema in Supabase

1. Go to https://supabase.com/dashboard/project/jfztroonldcqgmhitdyt
2. Navigate to **SQL Editor**
3. Click **New Query**
4. Copy the entire contents of `backend/database/schema.sql`
5. Paste into the SQL editor
6. Click **Run** (or press Ctrl+Enter)

**Expected Output:**
```
Success. No rows returned
```

This creates:
- ✅ `public.jobs` table
- ✅ `public.candidates` table
- ✅ Row Level Security (RLS) policies
- ✅ Indexes for performance
- ✅ Helper functions

---

## Step 2: Verify Tables Created

In Supabase dashboard:
1. Navigate to **Table Editor**
2. You should see two new tables:
   - `jobs` (columns: id, job_id, user_id, job_description, created_at, updated_at)
   - `candidates` (columns: id, job_id, candidate_id, name, email, role, rank, scores, enrichments, etc.)

---

## Step 3: Verify RLS Policies

1. Navigate to **Authentication** → **Policies**
2. Select `jobs` table - should show 4 policies:
   - ✅ Users can view their own jobs
   - ✅ Users can insert their own jobs
   - ✅ Users can update their own jobs
   - ✅ Users can delete their own jobs

3. Select `candidates` table - should show 4 policies:
   - ✅ Users can view candidates from their jobs
   - ✅ Users can insert candidates to their jobs
   - ✅ Users can update candidates in their jobs
   - ✅ Users can delete candidates from their jobs

---

## Step 4: Update Backend Configuration

Add Supabase database connection to `.env`:

```env
# Supabase Database (PostgreSQL)
SUPABASE_DB_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**To get your database URL:**
1. Go to Supabase dashboard → **Settings** → **Database**
2. Scroll to **Connection string** → **URI**
3. Copy the connection string
4. Replace `[YOUR-PASSWORD]` with your database password

---

## Step 5: Install Python Dependencies

```bash
cd backend
.\venv\Scripts\Activate.ps1
pip install psycopg2-binary asyncpg
```

---

## Step 6: Replace CandidateStore Implementation

The new implementation is in `backend/app/storage/candidate_store_pg.py`.

Update `backend/app/main.py` to use the new store:

```python
# OLD:
from app.storage.candidate_store import CandidateStore

# NEW:
from app.storage.candidate_store_pg import CandidateStorePG as CandidateStore
```

---

## Step 7: Test the Migration

1. Restart the backend server
2. Login to the frontend
3. Submit a new ranking job
4. Verify data is saved to Supabase:
   - Go to Supabase → **Table Editor** → `jobs`
   - You should see your job with `user_id` matching your auth user
   - Go to **Table Editor** → `candidates`
   - You should see ranked candidates for your job

---

## Step 8: Migrate Existing Data (Optional)

If you have existing jobs in `candidates.json` that you want to migrate:

```bash
cd backend
.\venv\Scripts\Activate.ps1
python database/migrate_json_to_pg.py
```

This script will:
1. Read `data/candidates.json`
2. Create jobs in Supabase (assigned to your user)
3. Create candidates for each job
4. Preserve all timestamps and data

---

## Rollback Plan

If something goes wrong, you can rollback:

1. **Revert code changes:**
   ```bash
   git checkout backend/app/main.py
   ```

2. **Drop tables in Supabase:**
   ```sql
   DROP TABLE IF EXISTS public.candidates CASCADE;
   DROP TABLE IF EXISTS public.jobs CASCADE;
   ```

3. **Restart backend** - it will use `candidates.json` again

---

## Verification Checklist

After migration, verify:

- [ ] Tables created in Supabase
- [ ] RLS policies active
- [ ] Backend connects to Supabase
- [ ] New jobs save to database
- [ ] Candidates save to database
- [ ] Users can only see their own jobs
- [ ] API responses unchanged (same JSON structure)
- [ ] Frontend works without changes

---

## Benefits After Migration

✅ **Multi-user support** - Each user sees only their jobs
✅ **Scalability** - PostgreSQL handles 1000+ jobs easily
✅ **Data integrity** - Foreign keys, constraints, transactions
✅ **Query performance** - Indexed searches, JSONB queries
✅ **Backup & recovery** - Supabase automatic backups
✅ **Production-ready** - No file system dependencies

---

## Troubleshooting

### Error: "relation 'public.jobs' does not exist"
- **Solution**: Run `schema.sql` in Supabase SQL Editor

### Error: "permission denied for table jobs"
- **Solution**: Check RLS policies are enabled and grants are applied

### Error: "new row violates row-level security policy"
- **Solution**: Ensure `user_id` matches `auth.uid()` when inserting jobs

### Error: "connection refused"
- **Solution**: Check `SUPABASE_DB_URL` in `.env` is correct

---

## Support

If you encounter issues:
1. Check Supabase logs: Dashboard → **Logs** → **Postgres Logs**
2. Check backend logs for SQL errors
3. Verify RLS policies are active
4. Test with Supabase SQL Editor first

---

## Next Steps

After successful migration:
1. ✅ Test full workflow (signup → login → submit job → view results)
2. ✅ Deploy to production
3. ✅ Remove `candidates.json` from version control (add to `.gitignore`)
4. ✅ Set up automated backups (Supabase does this automatically)
