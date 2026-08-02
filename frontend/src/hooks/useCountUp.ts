import { useEffect, useState } from 'react'

export function useCountUp(
  target: number,
  enabled: boolean,
  duration = 1500,
  decimals = 0,
) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!enabled) return

    let start: number | null = null
    let frame: number

    const step = (timestamp: number) => {
      if (!start) start = timestamp
      const progress = Math.min((timestamp - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Number((target * eased).toFixed(decimals)))
      if (progress < 1) frame = requestAnimationFrame(step)
    }

    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, enabled, duration, decimals])

  return value
}
