import { useEffect, useState } from 'react'

export function CustomCursor() {
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [hovering, setHovering] = useState(false)

  useEffect(() => {
    const move = (e: MouseEvent) => setPos({ x: e.clientX, y: e.clientY })

    const onOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      setHovering(
        !!target.closest('a, button, [role="button"], input, textarea, label'),
      )
    }

    window.addEventListener('mousemove', move)
    document.addEventListener('mouseover', onOver)
    return () => {
      window.removeEventListener('mousemove', move)
      document.removeEventListener('mouseover', onOver)
    }
  }, [])

  return (
    <>
      <div
        className="custom-cursor-dot hidden md:block"
        style={{ left: pos.x, top: pos.y }}
      />
      <div
        className="custom-cursor-ring hidden md:block"
        style={{
          left: pos.x,
          top: pos.y,
          width: hovering ? 48 : 32,
          height: hovering ? 48 : 32,
          borderColor: hovering
            ? 'rgba(26, 26, 24, 0.6)'
            : 'rgba(26, 26, 24, 0.35)',
        }}
      />
    </>
  )
}
