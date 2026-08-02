import { useState } from 'react'
import { motion } from 'framer-motion'

interface JDInputProps {
  onSubmit?: (jd: string) => void
}

export function JDInput({ onSubmit }: JDInputProps) {
  const [jd, setJd] = useState('')

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-editorial p-6"
    >
      <label className="text-sm font-medium text-ink">Job Description</label>
      <textarea
        value={jd}
        onChange={(e) => setJd(e.target.value)}
        placeholder="Paste job description here..."
        rows={6}
        className="mt-3 w-full resize-none rounded-lg border border-border bg-cream/30 p-4 text-sm text-ink outline-none placeholder:text-muted focus:border-ink/30"
      />
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        type="button"
        onClick={() => onSubmit?.(jd)}
        disabled={!jd.trim()}
        className="mt-4 rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-cream disabled:opacity-40"
      >
        Analyze Candidates
      </motion.button>
    </motion.div>
  )
}
