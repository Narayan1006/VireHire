import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Menu, Zap, Download } from 'lucide-react'
import { Sidebar } from '../components/Dashboard/Sidebar'
import { TopBar } from '../components/Dashboard/TopBar'
import { DatasetUpload, type UploadedDataset } from '../components/Dashboard/DatasetUpload'
import { StatsRow } from '../components/Dashboard/StatsRow'
import { CandidateTable } from '../components/Dashboard/CandidateTable'
import { TopCandidate } from '../components/Dashboard/TopCandidate'
import { Navbar } from '../components/shared/Navbar'
import {
  getStats,
  getCandidates,
  getBackendVersion,
  backendSupportsMultipartRank,
  triggerRanking,
  uploadCandidatesCsv,
  exportCandidates,
  pollUntilComplete,
  type Candidate,
  type DashboardStats,
} from '../services/api'

// ── Skeleton components ────────────────────────────────────────────────────

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="card-editorial p-5 animate-pulse">
          <div className="h-8 w-20 rounded bg-border" />
          <div className="mt-2 h-3 w-28 rounded bg-border/60" />
        </div>
      ))}
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="card-editorial overflow-hidden">
      <div className="border-b border-border px-6 py-4">
        <div className="h-6 w-40 rounded bg-border animate-pulse" />
      </div>
      <div className="divide-y divide-border">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-6 px-6 py-4 animate-pulse">
            <div className="h-5 w-8 rounded bg-border" />
            <div className="flex-1 space-y-1.5">
              <div className="h-4 w-36 rounded bg-border" />
              <div className="h-3 w-24 rounded bg-border/60" />
            </div>
            <div className="h-4 w-12 rounded bg-border" />
            <div className="h-4 w-12 rounded bg-border" />
            <div className="h-4 w-12 rounded bg-border" />
            <div className="h-4 w-12 rounded bg-border" />
            <div className="h-6 w-16 rounded-full bg-border" />
          </div>
        ))}
      </div>
    </div>
  )
}

function PipelineProgress({ estimated }: { estimated: number }) {
  return (
    <div className="card-editorial p-6">
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-ink border-t-transparent" />
        <div>
          <p className="font-medium text-ink">Pipeline running…</p>
          <p className="text-sm text-muted">
            Analyzing 9,500+ candidates · Est. {Math.round(estimated / 60)} min
          </p>
        </div>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full w-full animate-[shimmer_2s_linear_infinite] rounded-full bg-gradient-to-r from-transparent via-ink/20 to-transparent bg-[length:200%_100%]" />
      </div>
    </div>
  )
}

// ── Toast ──────────────────────────────────────────────────────────────────

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 5000)
    return () => clearTimeout(t)
  }, [onDismiss])
  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border border-border bg-white px-5 py-3.5 shadow-lg">
      <p className="text-sm text-ink">{message}</p>
    </div>
  )
}

// ── Dashboard ──────────────────────────────────────────────────────────────

const VERDICTS = ['ALL', 'HIRE', 'REVIEW', 'REJECT'] as const
type VerdictFilter = (typeof VERDICTS)[number]

const DEFAULT_STATS: DashboardStats = {
  totalCandidates: 0,
  avgScore: 0,
  verifiedProfiles: 0,
  timeSaved: '0 hrs',
  verdictBreakdown: { HIRE: 0, REVIEW: 0, REJECT: 0 },
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>(DEFAULT_STATS)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [dataset, setDataset] = useState<UploadedDataset | null>(null)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [jobDescription, setJobDescription] = useState('')
  const [loadingStats, setLoadingStats] = useState(true)
  const [loadingCandidates, setLoadingCandidates] = useState(true)
  const [isPipelining, setIsPipelining] = useState(false)
  const [estimatedTime, setEstimatedTime] = useState(900)
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('ALL')
  const [toast, setToast] = useState<string | null>(null)
  const [backendVersion, setBackendVersion] = useState<string | null>(null)
  const [stopPolling, setStopPolling] = useState<(() => void) | null>(null)

  const showToast = (msg: string) => setToast(msg)
  const dismissToast = useCallback(() => setToast(null), [])

  // Fetch stats
  const loadStats = useCallback(async () => {
    setLoadingStats(true)
    try {
      const data = await getStats()
      setStats(data)
    } catch (err) {
      showToast((err as Error).message)
    } finally {
      setLoadingStats(false)
    }
  }, [])

  // Fetch candidates
  const loadCandidates = useCallback(
    async (verdict?: string) => {
      setLoadingCandidates(true)
      try {
        const params: Parameters<typeof getCandidates>[0] = { limit: 50 }
        if (verdict && verdict !== 'ALL') params.verdict = verdict
        const data = await getCandidates(params)
        setCandidates(data.candidates)
      } catch (err) {
        showToast((err as Error).message)
        setCandidates([])
      } finally {
        setLoadingCandidates(false)
      }
    },
    [],
  )

  // On mount
  useEffect(() => {
    loadStats()
    loadCandidates()
    getBackendVersion()
      .then(setBackendVersion)
      .catch(() => setBackendVersion(null))
    return () => {
      stopPolling?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Verdict filter change
  const handleVerdictFilter = (v: VerdictFilter) => {
    setVerdictFilter(v)
    loadCandidates(v === 'ALL' ? undefined : v)
  }

  // CSV upload
  const handleDatasetUpload = async (file: File): Promise<UploadedDataset> => {
    const result = await uploadCandidatesCsv(file)
    const uploaded: UploadedDataset = {
      filePath: result.filePath,
      filename: result.filename,
      validCandidates: result.validCandidates,
      totalRows: result.totalRows,
    }
    setDataset(uploaded)
    setCsvFile(file)
    showToast(`Dataset loaded: ${result.validCandidates} candidates ready.`)
    return uploaded
  }

  const resolveCsvFile = async (): Promise<File> => {
    if (csvFile) return csvFile
    const res = await fetch('/sample-candidates.csv')
    if (!res.ok) throw new Error('Upload a CSV dataset or use the sample template first.')
    const blob = await res.blob()
    return new File([blob], 'sample-candidates.csv', { type: 'text/csv' })
  }

  // JD submit → trigger pipeline
  const handleJDSubmit = async () => {
    const jd = jobDescription.trim()
    if (jd.length < 50) {
      showToast('Job description must be at least 50 characters.')
      return
    }
    try {
      setIsPipelining(true)
      const file = await resolveCsvFile()
      const { job_id, estimated_time_seconds } = await triggerRanking(
        jd,
        file,
        dataset?.filePath,
      )
      setEstimatedTime(estimated_time_seconds ?? 900)

      const cleanup = pollUntilComplete(
        job_id,
        async () => {
          setIsPipelining(false)
          setStopPolling(null)
          await loadStats()
          await loadCandidates(verdictFilter === 'ALL' ? undefined : verdictFilter)
          showToast('Pipeline complete! Results updated.')
        },
        (err) => {
          setIsPipelining(false)
          setStopPolling(null)
          showToast(err)
        },
      )
      setStopPolling(() => cleanup)
    } catch (err) {
      setIsPipelining(false)
      showToast((err as Error).message)
    }
  }

  // Export CSV
  const handleExport = async () => {
    try {
      await exportCandidates(verdictFilter === 'ALL' ? undefined : verdictFilter)
    } catch (err) {
      showToast((err as Error).message)
    }
  }

  const topCandidate = candidates[0] ?? null

  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <div className="flex pt-[72px]">
        <Sidebar />

        <div className="flex min-h-[calc(100vh-72px)] flex-1 flex-col">
          {/* Mobile header */}
          <div className="flex items-center gap-3 border-b border-border bg-white px-6 py-4 lg:hidden">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-border"
              aria-label="Menu"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              <span className="font-instrument text-xl">VeriHire</span>
            </div>
          </div>

          <TopBar />

          <main className="flex-1 space-y-8 p-8">
            {backendVersion &&
              !backendSupportsMultipartRank(backendVersion) && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Backend API v{backendVersion} — upload your CSV before analyzing. Redeploy
                  Render from GitHub <code className="text-xs">main</code> to enable in-memory
                  ranking (v1.0.1+).
                </div>
              )}
            {/* Stats */}
            {loadingStats ? (
              <StatsSkeleton />
            ) : (
              <StatsRow stats={stats} />
            )}

            {/* Verdict filter + Export */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex gap-2">
                {VERDICTS.map((v) => (
                  <button
                    key={v}
                    onClick={() => handleVerdictFilter(v)}
                    className={`rounded-full border px-4 py-1.5 text-xs font-medium transition-colors ${
                      verdictFilter === v
                        ? 'border-ink bg-ink text-cream'
                        : 'border-border text-muted hover:border-ink/40 hover:text-ink'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
              <button
                onClick={handleExport}
                className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-1.5 text-xs font-medium text-muted transition-colors hover:border-ink/40 hover:text-ink"
              >
                <Download className="h-3.5 w-3.5" />
                Export CSV
              </button>
            </div>

            <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
              <div className="space-y-8 xl:col-span-2">
                {!isPipelining && (
                  <DatasetUpload
                    onUpload={handleDatasetUpload}
                    dataset={dataset}
                  />
                )}

                {/* JD input or pipeline progress */}
                {isPipelining ? (
                  <PipelineProgress estimated={estimatedTime} />
                ) : (
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card-editorial p-6"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <label className="text-sm font-medium text-ink" htmlFor="job-description">
                        Job Description
                      </label>
                      <span
                        className={`text-xs ${
                          jobDescription.trim().length >= 50 ? 'text-muted' : 'text-amber-700'
                        }`}
                      >
                        {jobDescription.trim().length}/50 min
                      </span>
                    </div>
                    <textarea
                      id="job-description"
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      onPaste={(e) => {
                        e.stopPropagation()
                      }}
                      placeholder="Paste job description here..."
                      rows={6}
                      className="mt-3 w-full resize-none rounded-lg border border-border bg-cream/30 p-4 text-sm text-ink outline-none placeholder:text-muted focus:border-ink/30"
                    />
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      type="button"
                      onClick={handleJDSubmit}
                      disabled={jobDescription.trim().length < 50}
                      className="mt-4 rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-cream disabled:opacity-40"
                    >
                      Analyze Candidates
                    </motion.button>
                  </motion.div>
                )}

                {/* Candidate table */}
                {loadingCandidates ? (
                  <TableSkeleton />
                ) : (
                  <CandidateTable candidates={candidates} />
                )}
              </div>

              {/* Top candidate panel */}
              <div>
                {topCandidate && !loadingCandidates && (
                  <TopCandidate candidate={topCandidate} />
                )}
              </div>
            </div>
          </main>
        </div>
      </div>

      {toast && <Toast message={toast} onDismiss={dismissToast} />}
    </div>
  )
}
