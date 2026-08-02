import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { cn } from '../../utils/cn'

interface EmailCaptureProps {
  className?: string
  variant?: 'default' | 'hero'
}

export function EmailCapture({
  className = '',
  variant = 'default',
}: EmailCaptureProps) {
  const [email, setEmail] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email) setEmail('')
  }

  return (
    <motion.form
      onSubmit={handleSubmit}
      className={cn(
        'glass-input mx-auto flex max-w-md items-center gap-2 rounded-full p-1.5 pl-5',
        variant === 'hero' && 'border-ink/10 bg-surface shadow-md shadow-ink/[0.08]',
        className,
      )}
    >
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your work email"
        className="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted-light"
        required
      />
      <motion.button
        type="submit"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Submit email"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-cream"
      >
        <ArrowRight className="h-4 w-4" />
      </motion.button>
    </motion.form>
  )
}
