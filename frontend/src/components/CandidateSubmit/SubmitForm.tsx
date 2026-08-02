import { motion } from 'framer-motion'
import { Upload } from 'lucide-react'
import { useState } from 'react'

export function SubmitForm() {
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card-editorial mx-auto max-w-lg p-10 text-center"
      >
        <h2 className="font-instrument text-2xl text-ink">Profile submitted</h2>
        <p className="mt-3 text-sm text-muted">
          We&apos;ll verify your GitHub and LeetCode signals and notify you when
          your profile is ready.
        </p>
      </motion.div>
    )
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      onSubmit={handleSubmit}
      className="card-editorial mx-auto max-w-lg p-8 md:p-10"
    >
      <h1 className="font-instrument text-3xl text-ink">Submit your profile</h1>
      <p className="mt-2 text-sm text-muted">
        Get ranked by proven capability — not keyword density.
      </p>

      <div className="mt-8 space-y-4">
        {[
          { name: 'fullName', label: 'Full name', type: 'text' },
          { name: 'email', label: 'Email', type: 'email' },
          { name: 'github', label: 'GitHub username', type: 'text' },
          { name: 'leetcode', label: 'LeetCode handle', type: 'text' },
        ].map((field) => (
          <div key={field.name}>
            <label className="text-xs font-medium text-muted">{field.label}</label>
            <input
              type={field.type}
              name={field.name}
              required
              className="mt-1 w-full rounded-lg border border-border bg-cream/30 px-4 py-2.5 text-sm text-ink outline-none focus:border-ink/30"
            />
          </div>
        ))}

        <div>
          <label className="text-xs font-medium text-muted">Resume (PDF)</label>
          <label className="mt-1 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-cream/30 px-4 py-8 transition-colors hover:bg-cream/60">
            <Upload className="h-6 w-6 text-muted" />
            <span className="mt-2 text-sm text-muted">Click to upload PDF</span>
            <input type="file" accept=".pdf" className="hidden" required />
          </label>
        </div>
      </div>

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        type="submit"
        className="mt-8 w-full rounded-full bg-ink py-3 text-sm font-medium text-cream"
      >
        Submit Profile
      </motion.button>
    </motion.form>
  )
}
