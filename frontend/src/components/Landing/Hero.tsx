import { motion } from 'framer-motion'
import { ChevronDown, Play, Box } from 'lucide-react'
import { GitHubIcon } from '../ui/SocialIcons'
import { Link } from 'react-router-dom'

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

const badges = [
  'Spring Boot',
  'React',
  'Python AI',
  'Supabase PostgreSQL',
  'JWT',
  'Docker',
  'ChromaDB',
  'LLMs',
]

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
        className="relative z-10 mx-auto max-w-5xl px-6 pt-28 pb-24 text-center"
      >
        <motion.p
          variants={fadeUp}
          className="mb-6 text-xs font-medium tracking-[0.22em] text-muted uppercase"
        >
          Open Source Hiring Intelligence Platform
        </motion.p>

        <motion.h1
          variants={fadeUp}
          className="font-instrument text-5xl leading-[1.1] text-ink sm:text-6xl md:text-7xl lg:text-[76px]"
        >
          Evidence-Based Candidate Ranking
          <br />
          <span className="text-muted text-4xl sm:text-5xl md:text-6xl lg:text-[60px]">Powered by a Three-Layer AI Pipeline</span>
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="mx-auto mt-8 max-w-3xl text-lg leading-relaxed text-muted"
        >
          VeriHire AI is a production-grade hiring intelligence platform that combines Spring Boot, a Python AI microservice, semantic retrieval, evidence verification and LLM reasoning to rank candidates using real engineering signals instead of resume keywords.
        </motion.p>

        <motion.div variants={fadeUp} className="mt-12 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/login"
            className="flex items-center gap-2 rounded-full bg-ink px-8 py-3.5 text-sm font-medium text-cream transition-transform hover:scale-105 active:scale-95"
          >
            <Play className="h-4 w-4 fill-current" />
            Live Demo
          </Link>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-full border border-border bg-white/50 px-8 py-3.5 text-sm font-medium text-ink backdrop-blur-md transition-all hover:bg-white hover:shadow-sm active:scale-95"
          >
            <GitHubIcon className="h-4 w-4" />
            GitHub Repository
          </a>
          <a
            href="#architecture"
            className="flex items-center gap-2 rounded-full border border-border bg-white/50 px-8 py-3.5 text-sm font-medium text-ink backdrop-blur-md transition-all hover:bg-white hover:shadow-sm active:scale-95"
          >
            <Box className="h-4 w-4" />
            Architecture
          </a>
        </motion.div>

        <motion.div variants={fadeUp} className="mt-16 flex flex-wrap items-center justify-center gap-3">
          {badges.map((badge) => (
            <span
              key={badge}
              className="rounded-md border border-border/60 bg-cream/30 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted backdrop-blur-sm transition-colors hover:border-ink/20 hover:text-ink"
            >
              {badge}
            </span>
          ))}
        </motion.div>
      </motion.div>

      <motion.a
        href="#how-it-works"
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
