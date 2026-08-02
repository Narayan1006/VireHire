import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import type { Candidate } from '../../types'
import { VerdictBadge } from '../ui/VerdictBadge'

interface CandidateTableProps {
  candidates: Candidate[]
}

export function CandidateTable({ candidates }: CandidateTableProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card-editorial overflow-hidden"
    >
      <div className="border-b border-border px-6 py-4">
        <h2 className="font-instrument text-xl text-ink">Candidate Rankings</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-muted uppercase tracking-wide">
              <th className="px-6 py-3 font-medium">Rank</th>
              <th className="px-6 py-3 font-medium">Name</th>
              <th className="px-6 py-3 font-medium">Percentile</th>
              <th className="px-6 py-3 font-medium">PR Score</th>
              <th className="px-6 py-3 font-medium">GitHub</th>
              <th className="px-6 py-3 font-medium">DSA</th>
              <th className="px-6 py-3 font-medium">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, i) => (
              <motion.tr
                key={c.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.05 * i }}
                onClick={() => navigate(`/candidate/${c.id}`)}
                className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-cream/80"
              >
                <td className="px-6 py-4 font-instrument text-lg text-ink">
                  #{c.rank}
                </td>
                <td className="px-6 py-4">
                  <p className="font-medium text-ink">{c.name}</p>
                  <p className="text-xs text-muted">{c.role}</p>
                </td>
                <td className="px-6 py-4 text-muted">{c.percentile}th</td>
                <td className="px-6 py-4 text-muted">{c.prScore}</td>
                <td className="px-6 py-4 text-muted">{c.github}</td>
                <td className="px-6 py-4 text-muted">{c.dsa}</td>
                <td className="px-6 py-4">
                  <VerdictBadge verdict={c.verdict} />
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}
