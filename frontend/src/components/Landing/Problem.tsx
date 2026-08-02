import { motion } from 'framer-motion'
import { useScrollSection } from '../../hooks/useScrollSection'

export function Problem() {
  const { ref, inView } = useScrollSection()

  return (
    <section id="problem" ref={ref} className="bg-white px-6 py-24 md:px-10 md:py-32">
      <motion.div
        initial={{ opacity: 0, y: 48 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="mx-auto max-w-4xl"
      >
        <p className="font-instrument text-[120px] leading-none text-muted/40">
          01
        </p>
        <h2 className="font-instrument mt-4 max-w-2xl text-4xl text-ink md:text-5xl">
          Keywords miss the best people.
        </h2>
        <p className="mt-8 max-w-xl text-base leading-relaxed text-muted">
          ATS systems answer: does this resume contain the right words? Nobody
          asks: can this person actually do the job?
        </p>
        <div className="section-divider mt-16" />
      </motion.div>
    </section>
  )
}
