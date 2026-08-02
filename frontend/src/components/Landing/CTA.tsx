import { motion } from 'framer-motion'
import { EmailCapture } from '../shared/EmailCapture'
import { useScrollSection } from '../../hooks/useScrollSection'

export function CTA() {
  const { ref, inView } = useScrollSection()

  return (
    <section ref={ref} className="bg-cream px-6 py-24 md:px-10 md:py-32">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
        className="mx-auto max-w-xl text-center"
      >
        <h2 className="font-instrument text-4xl text-ink md:text-5xl">
          Ready to hire by capability?
        </h2>
        <p className="mt-4 text-base text-muted">
          Join recruiters already using evidence-backed hiring.
        </p>
        <div className="mt-10">
          <EmailCapture />
        </div>
      </motion.div>
    </section>
  )
}
