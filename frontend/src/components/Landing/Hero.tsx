import { motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { EmailCapture } from '../shared/EmailCapture'

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const },
  },
}

export function Hero() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-cream">
      <div className="absolute inset-0">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="hero-video h-full w-full object-cover"
          src="/videos/bg.mp4"
        />
        <div className="hero-overlay absolute inset-0" />
        <div className="hero-content-scrim absolute inset-0" />
      </div>

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="relative z-10 mx-auto max-w-3xl px-6 pt-28 pb-24 text-center"
      >
        <motion.p
          variants={fadeUp}
          className="mb-6 text-xs font-medium tracking-[0.22em] text-muted uppercase"
        >
          Hiring intelligence platform
        </motion.p>

        <motion.h1
          variants={fadeUp}
          className="font-instrument text-5xl leading-[1.05] text-ink sm:text-6xl md:text-7xl lg:text-[80px]"
        >
          Rank by capability,
          <br />
          not keywords.
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="mx-auto mt-6 max-w-md text-base leading-relaxed text-muted"
        >
          VeriHire verifies every candidate claim against real GitHub and
          LeetCode signals — then ranks your entire pool by proven capability.
        </motion.p>

        <motion.div variants={fadeUp} className="mt-10">
          <EmailCapture variant="hero" />
        </motion.div>
      </motion.div>

      <motion.a
        href="#problem"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, y: [0, 8, 0] }}
        transition={{
          opacity: { delay: 1.2, duration: 0.5 },
          y: { delay: 1.2, duration: 1.5, repeat: Infinity },
        }}
        className="relative z-10 mb-10 flex flex-col items-center gap-1 text-muted"
        aria-label="Scroll down"
      >
        <ChevronDown className="h-5 w-5" />
      </motion.a>
    </section>
  )
}
