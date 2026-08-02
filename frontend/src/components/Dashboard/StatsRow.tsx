import { motion } from 'framer-motion'
import type { DashboardStats } from '../../types'

interface StatsRowProps {
  stats: DashboardStats
}

const items = [
  { key: 'totalCandidates' as const, label: 'Total Candidates' },
  { key: 'avgScore' as const, label: 'Avg PR Score', suffix: '' },
  { key: 'verifiedProfiles' as const, label: 'Verified Profiles' },
  { key: 'timeSaved' as const, label: 'Time Saved' },
]

export function StatsRow({ stats }: StatsRowProps) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {items.map((item, i) => (
        <motion.div
          key={item.key}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="card-editorial p-5"
        >
          <p className="font-instrument text-3xl text-ink">
            {stats[item.key]}
            {item.suffix ?? ''}
          </p>
          <p className="mt-1 text-xs text-muted">{item.label}</p>
        </motion.div>
      ))}
    </div>
  )
}

