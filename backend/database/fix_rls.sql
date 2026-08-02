-- Fix RLS policies to allow service role to bypass
-- Run this in Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view their own jobs" ON public.jobs;
DROP POLICY IF EXISTS "Users can insert their own jobs" ON public.jobs;
DROP POLICY IF EXISTS "Users can update their own jobs" ON public.jobs;
DROP POLICY IF EXISTS "Users can delete their own jobs" ON public.jobs;

DROP POLICY IF EXISTS "Users can view candidates from their jobs" ON public.candidates;
DROP POLICY IF EXISTS "Users can insert candidates to their jobs" ON public.candidates;
DROP POLICY IF EXISTS "Users can update candidates in their jobs" ON public.candidates;
DROP POLICY IF EXISTS "Users can delete candidates from their jobs" ON public.candidates;

-- Recreate policies with service role bypass
-- Jobs table policies
CREATE POLICY "Users can view their own jobs"
    ON public.jobs
    FOR SELECT
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR auth.uid() = user_id
    );

CREATE POLICY "Users can insert their own jobs"
    ON public.jobs
    FOR INSERT
    WITH CHECK (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR auth.uid() = user_id
    );

CREATE POLICY "Users can update their own jobs"
    ON public.jobs
    FOR UPDATE
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR auth.uid() = user_id
    )
    WITH CHECK (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR auth.uid() = user_id
    );

CREATE POLICY "Users can delete their own jobs"
    ON public.jobs
    FOR DELETE
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR auth.uid() = user_id
    );

-- Candidates table policies
CREATE POLICY "Users can view candidates from their jobs"
    ON public.candidates
    FOR SELECT
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert candidates to their jobs"
    ON public.candidates
    FOR INSERT
    WITH CHECK (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update candidates in their jobs"
    ON public.candidates
    FOR UPDATE
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    )
    WITH CHECK (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete candidates from their jobs"
    ON public.candidates
    FOR DELETE
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.job_id = candidates.job_id
            AND jobs.user_id = auth.uid()
        )
    );
