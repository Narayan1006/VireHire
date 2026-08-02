// VeriHire AI — API Service Layer
// Connects React frontend to FastAPI backend

import type { Candidate, DashboardStats } from '../types'

export type { Candidate, DashboardStats }

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function asAiLevel(value: string): Candidate['githubEvidence']['aiUsageLevel'] {
  if (value === 'Medium' || value === 'High') return value
  return 'Low'
}

function asSeverity(value: string): Candidate['riskFlags'][number]['severity'] {
  if (value === 'medium' || value === 'high') return value
  return 'low'
}

function asTimelineType(value: string): Candidate['timeline'][number]['type'] {
  return value === 'education' ? 'education' : 'experience'
}

// ── Error Handling ─────────────────────────────────────────────────────────

function parseApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') return fallback
  const b = body as Record<string, unknown>
  const detail = b.detail

  const fieldErrors = (
    b.details as { errors?: Array<{ field: string; message: string }> } | undefined
  )?.errors
  if (fieldErrors?.length) {
    return fieldErrors
      .map((e) => {
        const field = e.field.replace(/^(body|form) -> /, '')
        if (field === 'csv_file') {
          return 'CSV file is required — upload a dataset, then click Analyze.'
        }
        if (field === 'job_description') {
          return `Job description must be at least 50 characters (${e.message}).`
        }
        return `${field}: ${e.message}`
      })
      .join(' ')
  }

  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: string }).message)
  }
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e === 'object' && 'msg' in e ? String(e.msg) : ''))
      .filter(Boolean)
      .join('; ')
  }
  if (typeof b.message === 'string' && b.message !== 'Request validation failed') {
    return b.message
  }
  if (typeof b.message === 'string') return fallback
  return fallback
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>

  let message = 'Unknown error'
  try {
    const body = await res.json()
    message = parseApiError(body, res.statusText)
  } catch {
    message = res.statusText
  }

  if (res.status === 400) throw new Error(message)
  if (res.status === 404) {
    if (message === 'Unknown error' || message === 'Not Found') {
      throw new Error('Upload endpoint not found. Backend may need a redeploy.')
    }
    throw new Error(message)
  }
  if (res.status >= 500) throw new Error('Server error. Try again.')
  throw new Error(message)
}

// ── Auth token helpers ─────────────────────────────────────────────────────

const TOKEN_KEY = 'vh_access_token'

function getStoredToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

// ── Auth API functions ────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string
  user: { id: string; email: string }
}

export async function authLogin(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as Record<string, string>)?.detail || 'Login failed')
  }
  return res.json()
}

export async function authSignup(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as Record<string, string>)?.detail || 'Sign-up failed')
  }
  return res.json()
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = getStoredToken()
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json', ...authHeader },
      ...options,
    })
    return handleResponse<T>(res)
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error('Network error. Check if server is running.')
    }
    throw err
  }
}

// ── Backend Response Types (snake_case) ────────────────────────────────────

interface ApiCandidate {
  id?: string           // from list endpoint /api/candidates
  candidate_id?: string // from detail endpoint /api/candidates/{id}
  rank: number
  name: string
  email: string
  role: string
  percentile: number
  pr_score: number
  github_score: number
  dsa_score: number
  verdict: 'HIRE' | 'REVIEW' | 'REJECT'
  skills?: Array<{ name: string; claimed: number; verified: number }>
  skill_scores?: Array<{ name: string; claimed: number; verified: number }>
  github_evidence?: {
    verified: boolean
    repo_count: number
    languages: Array<{ name: string; percentage: number }>
    architecture_score: number
    ai_usage_level: string
    last_active: string
  }
  leetcode_stats?: {
    verified: boolean
    rating: number
    problems_solved: number
    consistency: number
    easy: number
    medium: number
    hard: number
  }
  timeline?: Array<{
    id?: string
    type: string
    title: string
    organization: string
    period: string
    description?: string
  }>
  risk_flags?: Array<{
    id?: string
    severity: string
    label: string
    description: string
  }>
  summary?: string
  online_links?: string
}

interface ApiStats {
  total_candidates: number
  avg_score: number
  verified_profiles: number
  time_saved: string
  verdict_breakdown: { HIRE: number; REVIEW: number; REJECT: number }
}

interface ApiRankResponse {
  job_id: string
  status: string
  estimated_time_seconds: number
}

interface ApiStatusResponse {
  status: 'processing' | 'completed' | 'failed'
  job_id: string
  result_count?: number
}

interface ApiCandidatesResponse {
  total: number
  candidates: ApiCandidate[]
}

// ── Mapping: Backend → Frontend ────────────────────────────────────────────

function mapCandidate(c: ApiCandidate): Candidate {
  const skills = (c.skill_scores ?? c.skills ?? []).map((s) => ({
    name: s.name,
    claimed: s.claimed ?? 80,
    verified: s.verified ?? 0,
  }))

  const gh = c.github_evidence ?? {
    verified: false,
    repo_count: 0,
    languages: [],
    architecture_score: 0,
    ai_usage_level: 'Low',
    last_active: 'N/A',
  }

  const lc = c.leetcode_stats ?? {
    verified: false,
    rating: 0,
    problems_solved: 0,
    consistency: 0,
    easy: 0,
    medium: 0,
    hard: 0,
  }

  return {
    id: c.id ?? c.candidate_id ?? '',
    rank: c.rank,
    name: c.name,
    email: c.email,
    role: c.role,
    percentile: Math.round(c.percentile ?? 0),
    prScore: c.pr_score,
    github: c.github_score,
    dsa: c.dsa_score,
    verdict: c.verdict,
    skills,
    githubEvidence: {
      verified: gh.verified,
      repoCount: gh.repo_count,
      languages: gh.languages,
      architectureScore: gh.architecture_score,
      aiUsageLevel: asAiLevel(gh.ai_usage_level),
      lastActive: gh.last_active,
    },
    leetcode: {
      rating: lc.rating,
      problemsSolved: lc.problems_solved,
      consistency: lc.consistency,
      easy: lc.easy,
      medium: lc.medium,
      hard: lc.hard,
    },
    timeline: (c.timeline ?? []).map((t, idx) => ({
      id: t.id ?? String(idx),
      type: asTimelineType(t.type),
      title: t.title,
      organization: t.organization,
      period: t.period,
      description: t.description,
    })),
    riskFlags: (c.risk_flags ?? []).map((f, idx) => ({
      id: f.id ?? String(idx),
      severity: asSeverity(f.severity),
      label: f.label,
      description: f.description,
    })),
    summary: c.summary ?? '',
  }
}

function mapStats(s: ApiStats): DashboardStats {
  return {
    totalCandidates: s.total_candidates,
    avgScore: s.avg_score,
    verifiedProfiles: s.verified_profiles,
    timeSaved: s.time_saved,
    verdictBreakdown: s.verdict_breakdown ?? { HIRE: 0, REVIEW: 0, REJECT: 0 },
  }
}

// ── API Functions ──────────────────────────────────────────────────────────

const MULTIPART_RANK_MIN_VERSION = '1.0.1'
let cachedBackendVersion: string | null = null

function versionGte(current: string, minimum: string): boolean {
  const parse = (v: string) => v.split('.').map((n) => parseInt(n, 10) || 0)
  const a = parse(current)
  const b = parse(minimum)
  for (let i = 0; i < 3; i++) {
    if (a[i] > b[i]) return true
    if (a[i] < b[i]) return false
  }
  return true
}

/** Read backend version from /api/health (cached). */
export async function getBackendVersion(): Promise<string> {
  if (cachedBackendVersion) return cachedBackendVersion
  try {
    const res = await fetch(`${BASE_URL}/api/health`)
    if (res.ok) {
      const data = (await res.json()) as { version?: string }
      cachedBackendVersion = data.version ?? '1.0.0'
      return cachedBackendVersion
    }
  } catch {
    /* use default */
  }
  cachedBackendVersion = '1.0.0'
  return cachedBackendVersion
}

export function backendSupportsMultipartRank(version: string): boolean {
  return versionGte(version, MULTIPART_RANK_MIN_VERSION)
}

export interface UploadCsvResult {
  filePath: string
  filename: string
  totalRows: number
  validCandidates: number
}

/** Upload recruiter candidate CSV dataset */
export async function uploadCandidatesCsv(file: File): Promise<UploadCsvResult> {
  const form = new FormData()
  form.append('file', file)

  try {
    const res = await fetch(`${BASE_URL}/api/upload/csv`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      let message = `Upload failed (${res.status})`
      try {
        const body = await res.json()
        message = parseApiError(body, message)
      } catch {
        message = res.statusText || message
      }
      throw new Error(message)
    }
    const data = (await res.json()) as {
      file_path: string
      filename: string
      total_rows: number
      valid_candidates: number
    }
    return {
      filePath: data.file_path,
      filename: data.filename,
      totalRows: data.total_rows,
      validCandidates: data.valid_candidates,
    }
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error('Network error. Check if server is running.')
    }
    throw err
  }
}

async function triggerRankingMultipart(
  jobDescription: string,
  csvFile: File,
): Promise<ApiRankResponse> {
  const form = new FormData()
  form.append('job_description', jobDescription)
  form.append('csv_file', csvFile)
  form.append('top_k', '200')
  form.append('llm_top_k', '50')

  // Add authentication token
  const token = getStoredToken()
  const headers: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {}

  const res = await fetch(`${BASE_URL}/api/rank`, { 
    method: 'POST', 
    headers,
    body: form 
  })
  if (!res.ok) {
    let message = 'Ranking request failed'
    try {
      const body = await res.json()
      message = parseApiError(body, message)
    } catch {
      message = res.statusText || message
    }
    throw new Error(message)
  }
  return res.json() as Promise<ApiRankResponse>
}

/** Legacy JSON rank (production v1.0.0 until Render deploys multipart API). */
async function triggerRankingLegacy(
  jobDescription: string,
  csvFilePath: string,
): Promise<ApiRankResponse> {
  return apiFetch<ApiRankResponse>('/api/rank', {
    method: 'POST',
    body: JSON.stringify({
      job_description: jobDescription,
      csv_file_path: csvFilePath,
      top_k: 200,
      llm_top_k: 50,
    }),
  })
}

/**
 * Trigger ranking. Uses in-memory CSV upload on API >= 1.0.1;
 * falls back to upload + server path on older Render deployments.
 */
export async function triggerRanking(
  jobDescription: string,
  csvFile: File,
  csvFilePath?: string,
): Promise<{
  job_id: string
  status: string
  estimated_time_seconds: number
}> {
  const version = await getBackendVersion()

  try {
    if (backendSupportsMultipartRank(version)) {
      return triggerRankingMultipart(jobDescription, csvFile)
    }

    let path = csvFilePath
    if (!path) {
      const uploaded = await uploadCandidatesCsv(csvFile)
      path = uploaded.filePath
    }
    return triggerRankingLegacy(jobDescription, path)
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error('Network error. Check if server is running.')
    }
    throw err
  }
}

/** Get the current status of a ranking job */
export async function getRankingStatus(jobId: string): Promise<ApiStatusResponse> {
  return apiFetch<ApiStatusResponse>(`/api/rank/${jobId}/status`)
}

/** Get ranked candidates with optional filters */
export async function getCandidates(params?: {
  verdict?: string
  min_score?: number
  limit?: number
  offset?: number
  job_id?: string
}): Promise<{ total: number; candidates: Candidate[] }> {
  const qs = new URLSearchParams()
  if (params?.verdict) qs.set('verdict', params.verdict)
  if (params?.min_score != null) qs.set('min_score', String(params.min_score))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  if (params?.offset != null) qs.set('offset', String(params.offset))
  if (params?.job_id) qs.set('job_id', params.job_id)

  const query = qs.toString() ? `?${qs.toString()}` : ''
  const data = await apiFetch<ApiCandidatesResponse>(`/api/candidates${query}`)
  return {
    total: data.total,
    candidates: data.candidates.map(mapCandidate),
  }
}

/** Get a single candidate by ID */
export async function getCandidateById(id: string): Promise<Candidate> {
  const data = await apiFetch<ApiCandidate>(`/api/candidates/${id}`)
  return mapCandidate(data)
}

/** Get dashboard stats */
export async function getStats(): Promise<DashboardStats> {
  const data = await apiFetch<ApiStats>('/api/stats')
  return mapStats(data)
}

/** Trigger a browser CSV download */
export async function exportCandidates(verdict?: string): Promise<void> {
  const qs = new URLSearchParams({ format: 'csv' })
  if (verdict) qs.set('verdict', verdict)

  try {
    const res = await fetch(`${BASE_URL}/api/export?${qs.toString()}`)
    if (!res.ok) throw new Error('Export failed')

    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `verehire_candidates${verdict ? `_${verdict.toLowerCase()}` : ''}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    throw new Error('Export failed. Try again.')
  }
}

/** Poll a job until completed or failed. Returns a cleanup function. */
export function pollUntilComplete(
  jobId: string,
  onComplete: () => void,
  onError?: (err: string) => void,
  intervalMs = 5000,
  timeoutMs = 30 * 60 * 1000,
): () => void {
  let stopped = false
  const start = Date.now()

  async function poll() {
    if (stopped) return
    if (Date.now() - start > timeoutMs) {
      onError?.('Pipeline timed out after 30 minutes')
      return
    }

    try {
      const { status } = await getRankingStatus(jobId)
      if (stopped) return
      if (status === 'completed') {
        onComplete()
        return
      }
      if (status === 'failed') {
        onError?.('Pipeline failed. Check server logs.')
        return
      }
      // Still processing — schedule next poll
      setTimeout(poll, intervalMs)
    } catch (err) {
      if (!stopped) {
        onError?.((err as Error).message)
      }
    }
  }

  // Start polling
  setTimeout(poll, intervalMs)

  // Return cleanup
  return () => {
    stopped = true
  }
}
