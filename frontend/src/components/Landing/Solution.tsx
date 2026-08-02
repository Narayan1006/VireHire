import { motion } from 'framer-motion'
import { CheckCircle2 } from 'lucide-react'
import { useScrollSection } from '../../hooks/useScrollSection'

const points = [
  'Resume claims extracted automatically',
  'GitHub + LeetCode signals verified in real time',
  'Ranked by proven capability — not keyword density',
]

export function Solution() {
  const { ref, inView } = useScrollSection()

  return (
    <section ref={ref} className="bg-cream px-6 py-24 md:px-10 md:py-32">
      <motion.div
        initial={{ opacity: 0, y: 48 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
        className="mx-auto max-w-4xl"
      >
        <p className="font-instrument text-[120px] leading-none text-muted/40">
          02
        </p>
        <h2 className="font-instrument mt-4 max-w-2xl text-4xl text-ink md:text-5xl">
          VeriHire doesn&apos;t match. It verifies.
        </h2>

        <div className="mt-14 space-y-8">
          {points.map((point, i) => (
            <motion.div
              key={point}
              initial={{ opacity: 0, x: -24 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.2 + i * 0.12 }}
              className="flex items-start gap-4 border-l border-ink pl-6"
            >
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-ink" />
              <p className="text-base text-ink">{point}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
