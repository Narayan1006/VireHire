import { useRef } from 'react'
import { useInView } from 'framer-motion'

export function useScrollSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' as const })
  return { ref, inView }
}
