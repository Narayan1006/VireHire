import { motion } from 'framer-motion'
import { BadgeCheck } from 'lucide-react'
import type { GitHubEvidence } from '../../types'

export function GitHubSection({ evidence }: { evidence: GitHubEvidence }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 }}
      className="card-editorial p-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-instrument text-xl text-ink">GitHub Evidence</h2>
        {evidence.verified && (
          <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
            <BadgeCheck className="h-4 w-4" />
            Verified
          </span>
        )}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[
          { label: 'Repositories', value: evidence.repoCount },
          { label: 'Architecture', value: evidence.architectureScore },
          { label: 'AI Usage', value: evidence.aiUsageLevel },
          { label: 'Last Active', value: evidence.lastActive },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-lg border border-border bg-cream/50 p-4"
          >
            <p className="font-instrument text-2xl text-ink">{item.value}</p>
            <p className="text-xs text-muted">{item.label}</p>
          </div>
        ))}
      </div>

      <p className="mt-6 text-sm font-medium text-ink">Languages</p>
      <div className="mt-3 space-y-2">
        {evidence.languages.map((lang) => (
          <div key={lang.name} className="flex items-center gap-3">
            <span className="w-24 text-xs text-muted">{lang.name}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-ink/70"
                style={{ width: `${lang.percentage}%` }}
              />
            </div>
            <span className="w-8 text-right text-xs text-muted">
              {lang.percentage}%
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
