import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { motion } from 'framer-motion'
import { SkillBars } from '../components/CandidateDetail/SkillBars'
import { GitHubSection } from '../components/CandidateDetail/GitHubSection'
import { LeetCodeSection } from '../components/CandidateDetail/LeetCodeSection'
import { RiskFlags } from '../components/CandidateDetail/RiskFlags'
import { LLMSummary } from '../components/CandidateDetail/LLMSummary'
import { VerdictBadge } from '../components/ui/VerdictBadge'
import { Navbar } from '../components/shared/Navbar'
import { getCandidateById, type Candidate } from '../services/api'

// ── Skeleton ───────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="border-b border-border pb-8">
        <div className="h-5 w-20 rounded bg-border" />
        <div className="mt-4 h-12 w-64 rounded bg-border" />
        <div className="mt-3 h-4 w-40 rounded bg-border/60" />
      </div>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="card-editorial p-6">
          <div className="h-5 w-32 rounded bg-border" />
          <div className="mt-4 space-y-3">
            <div className="h-4 w-full rounded bg-border/60" />
            <div className="h-4 w-3/4 rounded bg-border/60" />
            <div className="h-4 w-5/6 rounded bg-border/60" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── CandidateDetail ────────────────────────────────────────────────────────

export function CandidateDetail() {
  const { id } = useParams<{ id: string }>()
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const data = await getCandidateById(id!)
        if (!cancelled) setCandidate(data)
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen bg-cream">
        <Navbar />
        <div className="mx-auto max-w-4xl px-6 pb-16 pt-28 md:px-8">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-sm text-muted transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to rankings
          </Link>
          <div className="mt-8">
            <DetailSkeleton />
          </div>
        </div>
      </div>
    )
  }

  if (error || !candidate) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-cream gap-4">
        <p className="font-instrument text-2xl text-ink">
          {error ?? 'Candidate not found'}
        </p>
        <p className="text-sm text-muted">{id}</p>
        <Link to="/dashboard" className="mt-2 text-sm text-muted hover:text-ink">
          ← Back to dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <div className="mx-auto max-w-4xl px-6 pb-16 pt-28 md:px-8">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to rankings
        </Link>

        <motion.header
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 border-b border-border pb-8"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm text-muted">Rank #{candidate.rank}</p>
              <h1 className="font-instrument text-4xl text-ink md:text-5xl">
                {candidate.name}
              </h1>
              <p className="mt-2 text-muted">{candidate.role}</p>
              {candidate.email && (
                <p className="mt-1 text-xs text-muted">{candidate.email}</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="rounded-full border border-border px-4 py-1.5 text-sm text-ink">
                {candidate.percentile}th percentile
              </span>
              <VerdictBadge verdict={candidate.verdict} />
            </div>
          </div>

          {/* Score summary row */}
          <div className="mt-6 flex flex-wrap gap-6">
            <div className="text-center">
              <p className="font-instrument text-2xl text-ink">{candidate.prScore}</p>
              <p className="text-xs text-muted">PR Score</p>
            </div>
            <div className="text-center">
              <p className="font-instrument text-2xl text-ink">{candidate.github}</p>
              <p className="text-xs text-muted">GitHub</p>
            </div>
            <div className="text-center">
              <p className="font-instrument text-2xl text-ink">{candidate.dsa}</p>
              <p className="text-xs text-muted">DSA</p>
            </div>
          </div>
        </motion.header>

        <div className="mt-8 space-y-6">
          <SkillBars skills={candidate.skills} />
          <GitHubSection evidence={candidate.githubEvidence} />
          <LeetCodeSection stats={candidate.leetcode} />
          <RiskFlags flags={candidate.riskFlags} />
          <LLMSummary summary={candidate.summary} />
        </div>
      </div>
    </div>
  )
}
