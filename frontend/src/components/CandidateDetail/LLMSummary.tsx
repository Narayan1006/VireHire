import { motion } from 'framer-motion'

export function LLMSummary({ summary }: { summary: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card-editorial p-6"
    >
      <h2 className="font-instrument text-xl text-ink">LLM Recruiter Summary</h2>
      <p className="mt-4 text-sm leading-relaxed text-muted italic">
        &ldquo;{summary}&rdquo;
      </p>
    </motion.div>
  )
}
