import type { Verdict } from '../../types'
import { cn } from '../../utils/cn'

const styles: Record<Verdict, string> = {
  HIRE: 'bg-emerald-100 text-emerald-800',
  REVIEW: 'bg-amber-100 text-amber-800',
  REJECT: 'bg-red-100 text-red-800',
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={cn(
        'inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
        styles[verdict],
      )}
    >
      {verdict}
    </span>
  )
}
