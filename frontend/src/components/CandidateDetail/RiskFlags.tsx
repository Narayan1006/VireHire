import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import type { RiskFlag } from '../../types'

export function RiskFlags({ flags }: { flags: RiskFlag[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="card-editorial p-6"
    >
      <h2 className="font-instrument text-xl text-ink">Risk Flags</h2>

      {flags.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No inconsistencies detected.</p>
      ) : (
        <div className="mt-6 space-y-3">
          {flags.map((flag) => (
            <div
              key={flag.id}
              className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
              <div>
                <p className="text-sm font-medium text-amber-900">
                  {flag.label}
                </p>
                <p className="mt-1 text-sm text-amber-800/80">
                  {flag.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
