import { motion } from 'framer-motion'
import { useScrollSection } from '../../hooks/useScrollSection'

const steps = [
  {
    num: '01',
    title: 'Paste job description',
    desc: 'Recruiter defines the role',
  },
  {
    num: '02',
    title: 'Upload candidate pool',
    desc: 'CSV or direct resume upload',
  },
  {
    num: '03',
    title: 'Get verified ranking',
    desc: 'Shortlist ranked by evidence',
  },
]

export function HowItWorks() {
  const { ref, inView } = useScrollSection()

  return (
    <section
      id="how-it-works"
      ref={ref}
      className="bg-white px-6 py-24 md:px-10 md:py-32"
    >
      <motion.div
        initial={{ opacity: 0, y: 48 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
        className="mx-auto max-w-6xl"
      >
        <p className="font-instrument text-[120px] leading-none text-muted/40">
          03
        </p>
        <h2 className="font-instrument mt-4 text-4xl text-ink md:text-5xl">
          Three steps. Zero guesswork.
        </h2>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-3">
          {steps.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 32 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.15 + i * 0.1 }}
              className="card-editorial p-8"
            >
              <span className="text-xs tracking-widest text-muted">
                {step.num}
              </span>
              <h3 className="font-instrument mt-4 text-2xl text-ink">
                {step.title}
              </h3>
              <p className="mt-3 text-sm text-muted">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
