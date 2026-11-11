-- =============================================================================
-- VeriHire AI — Supabase Row-Level Security (RLS) Hardening Script
-- Project: Virehire
-- Reference: qwyqemvadtbeoktzldon
-- Resolves: Critical Security Alert "Table publicly accessible (rls_disabled_in_public)"
-- =============================================================================

-- STEP 1: Enable Row Level Security on all application tables
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_settings ENABLE ROW LEVEL SECURITY;

-- STEP 2: Revoke anonymous public PostgREST API access
-- This ensures unauthenticated public internet requests cannot read, insert,
-- update, or delete records in your database tables.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;

-- STEP 3: Grant access to service_role and postgres superuser
-- The FastAPI backend (connecting via DATABASE_URL session pooler) connects
-- using postgres / service_role credentials and retains full database access.
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role, postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role, postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role, postgres;

-- STEP 4: Verification query
-- Run this check to verify all public tables now have RLS enabled (rowsecurity = true)
SELECT 
    schemaname, 
    tablename, 
    rowsecurity AS rls_enabled
FROM pg_tables 
WHERE schemaname = 'public';

