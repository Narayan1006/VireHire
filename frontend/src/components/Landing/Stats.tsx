import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { useCountUp } from '../../hooks/useCountUp'

const stats = [
  { value: 9500, suffix: '+', label: 'Candidates ranked', decimals: 0 },
  { value: 94, suffix: '%', label: 'Signal accuracy', decimals: 0 },
  { value: 80, suffix: '%', label: 'Time saved', decimals: 0 },
  { value: 3, suffix: '', label: 'Platforms verified', decimals: 0 },
]

function StatItem({
  value,
  suffix,
  label,
  decimals,
  enabled,
}: {
  value: number
  suffix: string
  label: string
  decimals: number
  enabled: boolean
}) {
  const count = useCountUp(value, enabled, 1500, decimals)
  const display =
    suffix === '+' ? `${count.toLocaleString()}${suffix}` : `${count}${suffix}`

  return (
    <div className="text-center md:text-left">
      <p className="font-instrument text-5xl text-white md:text-6xl">
        {display}
      </p>
      <p className="mt-2 text-sm text-white/60">{label}</p>
    </div>
  )
}

export function Stats() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section id="signals" ref={ref} className="bg-ink px-6 py-24 md:px-10 md:py-32">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-12 md:grid-cols-4 md:gap-8">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: i * 0.1 }}
          >
            <StatItem {...stat} enabled={inView} />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
