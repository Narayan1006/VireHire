-- ============================================================================
-- VireHire AI - Supabase Database Schema
-- ============================================================================
-- This schema migrates candidate/job persistence from candidates.json to PostgreSQL.
-- 
-- Tables:
--   - jobs: Stores ranking job submissions (job_id, user_id, job_description, timestamp)
--   - candidates: Stores ranked candidates with all enrichments (belongs to jobs)
--
-- Security:
--   - Row Level Security (RLS) enabled on both tables
--   - Users can only access their own jobs and candidates
--
-- ============================================================================

-- ============================================================================
-- 1. JOBS TABLE
-- ============================================================================
-- Stores ranking job submissions. Each job belongs to a user.
-- Replaces the "jobs" array in candidates.json

CREATE TABLE IF NOT EXISTS public.jobs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Job identification (8-char hex ID from frontend)
    job_id TEXT NOT NULL UNIQUE,
    
    -- User ownership (references auth.users)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Job details
    job_description TEXT NOT NULL DEFAULT '',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT jobs_job_id_key UNIQUE (job_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON public.jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON public.jobs(created_at DESC);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON public.jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 2. CANDIDATES TABLE
-- ============================================================================
-- Stores ranked candidates with all enrichments from the 3-layer pipeline.
-- Each candidate belongs to a job.
-- Replaces the "candidates" array in candidates.json

CREATE TABLE IF NOT EXISTS public.candidates (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to jobs
    job_id TEXT NOT NULL REFERENCES public.jobs(job_id) ON DELETE CASCADE,
    
    -- Candidate identification (from CSV)
    candidate_id TEXT NOT NULL,
    
    -- Basic info
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    
    -- Ranking
    rank INTEGER NOT NULL CHECK (rank >= 1),
    percentile INTEGER NOT NULL CHECK (percentile >= 0 AND percentile <= 100),
    
    -- Scores
    pr_score INTEGER NOT NULL CHECK (pr_score >= 0 AND pr_score <= 100),
    github_score INTEGER NOT NULL CHECK (github_score >= 0 AND github_score <= 100),
    dsa_score INTEGER NOT NULL CHECK (dsa_score >= 0 AND dsa_score <= 100),
    
    -- Verdict
    verdict TEXT NOT NULL CHECK (verdict IN ('HIRE', 'REVIEW', 'REJECT')),
    
    -- Enrichments (stored as JSONB for flexibility)
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    github_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    leetcode JSONB NOT NULL DEFAULT '{}'::jsonb,
    codeforces JSONB DEFAULT NULL,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary TEXT NOT NULL DEFAULT '',
    
    -- Layer scores
    layer1_score DOUBLE PRECISION NOT NULL CHECK (layer1_score >= 0.0 AND layer1_score <= 1.0),
    layer2_score DOUBLE PRECISION NOT NULL CHECK (layer2_score >= 0.0 AND layer2_score <= 1.0),
    layer3_confidence DOUBLE PRECISION NOT NULL CHECK (layer3_confidence >= 0.0 AND layer3_confidence <= 1.0),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one candidate_id per job
    CONSTRAINT candidates_job_candidate_unique UNIQUE (job_id, candidate_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON public.candidates(job_id);
CREATE INDEX IF NOT EXISTS idx_candidates_rank ON public.candidates(job_id, rank);
CREATE INDEX IF NOT EXISTS idx_candidates_verdict ON public.candidates(job_id, verdict);
CREATE INDEX IF NOT EXISTS idx_candidates_pr_score ON public.candidates(job_id, pr_score DESC);

-- JSONB indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_candidates_skills ON public.candidates USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_candidates_github_evidence ON public.candidates USING GIN (github_evidence);

-- ============================================================================
-- 3. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on both tables
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidates ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3.1 JOBS TABLE POLICIES
-- ============================================================================

-- Policy: Users can view only their own jobs
CREATE POLICY "Users can view their own jobs"
    ON public.jobs
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own jobs
CREATE POLICY "Users can insert their own jobs"
    ON public.jobs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own jobs
CREATE POLICY "Users can update their own jobs"
    ON public.jobs
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can delete their own jobs
CREATE POLICY "Users can delete their own jobs"
    ON public.jobs
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 3.2 CANDIDATES TABLE POLICIES
-- ============================================================================

-- Policy: Users can view candidates belonging to their jobs
CREATE POLICY "Users can view candidates from their jobs"
    ON public.candidates
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

-- Policy: Users can insert candidates to their jobs
CREATE POLICY "Users can insert candidates to their jobs"
    ON public.candidates
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

-- Policy: Users can update candidates in their jobs
CREATE POLICY "Users can update candidates in their jobs"
    ON public.candidates
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

-- Policy: Users can delete candidates from their jobs
CREATE POLICY "Users can delete candidates from their jobs"
    ON public.candidates
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

-- ============================================================================
-- 4. HELPER FUNCTIONS
-- ============================================================================

-- Function: Get job with candidate count
CREATE OR REPLACE FUNCTION get_job_with_stats(p_job_id TEXT)
RETURNS TABLE (
    job_id TEXT,
    job_description TEXT,
    created_at TIMESTAMPTZ,
    candidate_count BIGINT,
    hire_count BIGINT,
    review_count BIGINT,
    reject_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        j.job_id,
        j.job_description,
        j.created_at,
        COUNT(c.id) AS candidate_count,
        COUNT(c.id) FILTER (WHERE c.verdict = 'HIRE') AS hire_count,
        COUNT(c.id) FILTER (WHERE c.verdict = 'REVIEW') AS review_count,
        COUNT(c.id) FILTER (WHERE c.verdict = 'REJECT') AS reject_count
    FROM public.jobs j
    LEFT JOIN public.candidates c ON j.job_id = c.job_id
    WHERE j.job_id = p_job_id
    AND j.user_id = auth.uid()
    GROUP BY j.job_id, j.job_description, j.created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Delete old jobs (90-day retention)
CREATE OR REPLACE FUNCTION delete_expired_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM public.jobs
        WHERE created_at < NOW() - INTERVAL '90 days'
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 5. COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE public.jobs IS 'Stores ranking job submissions. Each job belongs to a user (auth.users).';
COMMENT ON TABLE public.candidates IS 'Stores ranked candidates with enrichments from the 3-layer pipeline. Each candidate belongs to a job.';

COMMENT ON COLUMN public.jobs.job_id IS '8-character hex ID generated by frontend (e.g., "3d419e2a")';
COMMENT ON COLUMN public.jobs.user_id IS 'References auth.users(id). User who submitted the job.';
COMMENT ON COLUMN public.jobs.job_description IS 'Job description text provided by the user';

COMMENT ON COLUMN public.candidates.candidate_id IS 'Candidate ID from CSV (e.g., "560dbc11")';
COMMENT ON COLUMN public.candidates.rank IS 'Sequential rank starting from 1 (1 = best candidate)';
COMMENT ON COLUMN public.candidates.percentile IS 'Percentile score (0-100)';
COMMENT ON COLUMN public.candidates.pr_score IS 'Overall PR score (0-100)';
COMMENT ON COLUMN public.candidates.verdict IS 'Hiring verdict: HIRE, REVIEW, or REJECT';
COMMENT ON COLUMN public.candidates.skills IS 'JSONB array of SkillConfidence objects';
COMMENT ON COLUMN public.candidates.github_evidence IS 'JSONB object with GitHub verification data';
COMMENT ON COLUMN public.candidates.leetcode IS 'JSONB object with LeetCode stats';
COMMENT ON COLUMN public.candidates.codeforces IS 'JSONB object with Codeforces stats (nullable)';
COMMENT ON COLUMN public.candidates.timeline IS 'JSONB array of TimelineEntry objects';
COMMENT ON COLUMN public.candidates.risk_flags IS 'JSONB array of RiskFlag objects';
COMMENT ON COLUMN public.candidates.summary IS 'LLM-generated explanation (100-300 words)';

-- ============================================================================
-- 6. GRANTS (Permissions)
-- ============================================================================

-- Grant authenticated users access to tables
GRANT SELECT, INSERT, UPDATE, DELETE ON public.jobs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.candidates TO authenticated;

-- Grant usage on sequences (for UUID generation)
GRANT USAGE ON SCHEMA public TO authenticated;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
