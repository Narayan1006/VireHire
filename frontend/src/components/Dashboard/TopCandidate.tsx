import { motion } from 'framer-motion'
import { BadgeCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Candidate } from '../../types'
import { VerdictBadge } from '../ui/VerdictBadge'

interface TopCandidateProps {
  candidate: Candidate
}

function SkillBar({
  name,
  verified,
  claimed,
}: {
  name: string
  verified: number
  claimed: number
}) {
  const isVerified = verified >= claimed - 10
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-ink">{name}</span>
        <span className={isVerified ? 'text-emerald-700' : 'text-amber-700'}>
          {verified}% {isVerified ? 'Verified' : 'Claimed'}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-border">
        <div
          className={`h-full rounded-full ${isVerified ? 'bg-emerald-500' : 'bg-amber-400'}`}
          style={{ width: `${verified}%` }}
        />
      </div>
    </div>
  )
}

export function TopCandidate({ candidate }: TopCandidateProps) {
  const topSkills = candidate.skills.slice(0, 2)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="card-editorial p-6"
    >
      <p className="text-xs tracking-widest text-muted uppercase">
        Top Candidate
      </p>
      <div className="mt-3 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-instrument text-2xl text-ink">{candidate.name}</h2>
          <p className="text-sm text-muted">{candidate.role}</p>
        </div>
        <span className="rounded-full border border-border px-3 py-1 text-xs font-medium text-ink">
          {candidate.percentile}th
        </span>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <VerdictBadge verdict={candidate.verdict} />
        {candidate.githubEvidence.verified && (
          <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
            <BadgeCheck className="h-3.5 w-3.5" />
            GitHub verified
          </span>
        )}
      </div>

      <div className="mt-6 space-y-4">
        {topSkills.map((s) => (
          <SkillBar
            key={s.name}
            name={s.name.split(' ')[0]}
            verified={s.verified}
            claimed={s.claimed}
          />
        ))}
      </div>

      <p className="mt-6 text-sm leading-relaxed text-muted italic">
        {candidate.summary.slice(0, 200)}…
      </p>

      <Link
        to={`/candidate/${candidate.id}`}
        className="mt-6 inline-block text-sm font-medium text-ink underline-offset-2 hover:underline"
      >
        View full profile →
      </Link>
    </motion.div>
  )
}
