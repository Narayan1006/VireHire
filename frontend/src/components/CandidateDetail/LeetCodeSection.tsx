import { motion } from 'framer-motion'
import type { LeetCodeStats } from '../../types'

export function LeetCodeSection({ stats }: { stats: LeetCodeStats }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="card-editorial p-6"
    >
      <h2 className="font-instrument text-xl text-ink">LeetCode</h2>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-cream/50 p-4 text-center">
          <p className="font-instrument text-2xl text-ink">{stats.rating}</p>
          <p className="text-xs text-muted">Rating</p>
        </div>
        <div className="rounded-lg border border-border bg-cream/50 p-4 text-center">
          <p className="font-instrument text-2xl text-ink">
            {stats.problemsSolved}
          </p>
          <p className="text-xs text-muted">Problems Solved</p>
        </div>
        <div className="rounded-lg border border-border bg-cream/50 p-4 text-center">
          <p className="font-instrument text-2xl text-ink">
            {stats.consistency}%
          </p>
          <p className="text-xs text-muted">Consistency</p>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        {[
          { label: 'Easy', count: stats.easy },
          { label: 'Medium', count: stats.medium },
          { label: 'Hard', count: stats.hard },
        ].map((t) => (
          <div
            key={t.label}
            className="flex flex-1 flex-col items-center rounded-lg border border-border py-3"
          >
            <p className="font-instrument text-lg text-ink">{t.count}</p>
            <p className="text-xs text-muted">{t.label}</p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
