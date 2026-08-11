import { useRef } from 'react'
import { motion, useScroll, useTransform, MotionValue } from 'framer-motion'
import { Database, FileText, Server, Brain, Activity, Search, LineChart, Code2, Cpu } from 'lucide-react'

const steps = [
  { icon: FileText, title: 'CSV Upload', desc: 'Recruiter uploads a dataset of candidates', color: 'text-zinc-600', bg: 'bg-zinc-100' },
  { icon: Server, title: 'Spring Boot Backend', desc: 'REST API handles multipart upload and auth', color: 'text-emerald-600', bg: 'bg-emerald-100' },
  { icon: Database, title: 'Neon PostgreSQL', desc: 'Stores Job metadata and async job state', color: 'text-teal-600', bg: 'bg-teal-100' },
  { icon: Cpu, title: 'Python AI Service', desc: 'Stateless FastAPI engine receives job payload', color: 'text-blue-600', bg: 'bg-blue-100' },
  { icon: Search, title: 'Layer 1: Semantic Retrieval', desc: 'ChromaDB filters out irrelevant resumes', color: 'text-violet-600', bg: 'bg-violet-100' },
  { icon: Code2, title: 'Layer 2: Evidence Verification', desc: 'Queries GitHub, LeetCode, and Codeforces', color: 'text-orange-600', bg: 'bg-orange-100' },
  { icon: Brain, title: 'Layer 3: LLM Reasoning', desc: 'Groq/Ollama evaluates context and issues verdicts', color: 'text-pink-600', bg: 'bg-pink-100' },
  { icon: Activity, title: 'Candidate Ranking', desc: 'Candidates scored across PRs, DSA, and ML rankings', color: 'text-amber-600', bg: 'bg-amber-100' },
  { icon: LineChart, title: 'Dashboard', desc: 'Recruiter views actionable technical insights', color: 'text-ink', bg: 'bg-ink/10' }
]

interface Step {
  icon: React.ElementType;
  title: string;
  desc: string;
  color: string;
  bg: string;
}

function StepCard({ step, index, totalSteps, scrollYProgress }: { step: Step, index: number, totalSteps: number, scrollYProgress: MotionValue<number> }) {
  const stepTarget = index / (totalSteps - 1)
  
  const range: number[] = []
  const outputOpacity: number[] = []
  const outputScale: number[] = []
  const outputY: number[] = []
  const outputZIndex: number[] = []

  if (index === 0) {
    range.push(0, 0.1, 1)
    outputOpacity.push(1, 0.2, 0.2)
    outputScale.push(1, 0.9, 0.9)
    outputY.push(0, -20, -20)
    outputZIndex.push(10, 0, 0)
  } else if (index === totalSteps - 1) {
    range.push(0, stepTarget - 0.1, stepTarget)
    outputOpacity.push(0.2, 0.2, 1)
    outputScale.push(0.9, 0.9, 1)
    outputY.push(20, 20, 0)
    outputZIndex.push(0, 0, 10)
  } else {
    range.push(0, stepTarget - 0.1, stepTarget, stepTarget + 0.1, 1)
    outputOpacity.push(0.2, 0.2, 1, 0.2, 0.2)
    outputScale.push(0.9, 0.9, 1, 0.9, 0.9)
    outputY.push(20, 20, 0, -20, -20)
    outputZIndex.push(0, 0, 10, 0, 0)
  }

  const opacity = useTransform(scrollYProgress, range, outputOpacity)
  const scale = useTransform(scrollYProgress, range, outputScale)
  const y = useTransform(scrollYProgress, range, outputY)
  const zIndex = useTransform(scrollYProgress, range, outputZIndex)

  return (
    <motion.div 
      className="absolute w-full flex items-center gap-8 px-4"
      style={{ opacity, scale, y, zIndex, top: '50%', marginTop: '-50px' }}
    >
      <div className={`relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-border/50 shadow-sm ${step.bg} ${step.color}`}>
        <step.icon className="h-5 w-5" />
      </div>
      <div className="card-editorial flex-1 p-6 backdrop-blur-md bg-white/80 border-border/50 shadow-sm transition-shadow">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[10px] font-bold tracking-widest text-muted uppercase">Step 0{index + 1}</span>
        </div>
        <h3 className="font-instrument text-2xl text-ink mb-1">{step.title}</h3>
        <p className="text-sm text-muted">{step.desc}</p>
      </div>
    </motion.div>
  )
}

export function HowItWorks() {
  const containerRef = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end']
  })

  return (
    <section id="how-it-works" ref={containerRef} className="relative bg-white" style={{ height: '300vh' }}>
      <div className="sticky top-0 h-screen w-full flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="relative z-10 mx-auto w-full max-w-5xl px-6 flex flex-col md:flex-row items-center gap-16">
          <div className="w-full md:w-1/3 text-center md:text-left">
            <h2 className="font-instrument text-4xl text-ink md:text-5xl lg:text-6xl leading-tight">The Data Flow</h2>
            <p className="mt-6 text-base text-muted max-w-sm mx-auto md:mx-0">
              Watch a single CSV file travel through our production pipeline, passing through microservices, vector databases, and multi-layered AI verification.
            </p>
          </div>
          <div className="relative w-full md:w-2/3 h-[600px] flex items-center">
            <div className="absolute left-[39px] top-10 bottom-10 w-0.5 bg-border rounded-full overflow-hidden">
              <motion.div className="w-full bg-ink origin-top" style={{ scaleY: scrollYProgress }}></motion.div>
            </div>
            <div className="relative w-full h-full flex flex-col justify-between py-10">
              {steps.map((step, index) => (
                <StepCard key={step.title} step={step} index={index} totalSteps={steps.length} scrollYProgress={scrollYProgress} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
