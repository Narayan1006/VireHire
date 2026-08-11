import { motion } from 'framer-motion'
import { Server, Database, Brain, Layout, Cpu, Code, Layers } from 'lucide-react'

const nodes = [
  {
    id: 'frontend',
    title: 'React Frontend',
    icon: Layout,
    desc: 'SPA with Framer Motion, Tailwind CSS. JWT authenticated.',
    col: 1,
    row: 1,
    color: 'bg-blue-100 text-blue-600 border-blue-200'
  },
  {
    id: 'spring',
    title: 'Spring Boot Backend',
    icon: Server,
    desc: 'Handles REST APIs, authentication, and async job orchestration.',
    col: 2,
    row: 1,
    color: 'bg-emerald-100 text-emerald-600 border-emerald-200'
  },
  {
    id: 'neon',
    title: 'Neon PostgreSQL',
    icon: Database,
    desc: 'Serverless PostgreSQL — stores users, settings (AES-256 encrypted), and job states.',
    col: 2,
    row: 2,
    color: 'bg-teal-100 text-teal-600 border-teal-200'
  },
  {
    id: 'python',
    title: 'Python AI Service',
    icon: Cpu,
    desc: 'Stateless FastAPI microservice running the 3-Layer pipeline.',
    col: 3,
    row: 1,
    color: 'bg-violet-100 text-violet-600 border-violet-200'
  },
  {
    id: 'chroma',
    title: 'ChromaDB',
    icon: Layers,
    desc: 'Vector DB for semantic retrieval of resumes (Layer 1).',
    col: 4,
    row: 1,
    color: 'bg-zinc-100 text-zinc-600 border-zinc-200'
  },
  {
    id: 'apis',
    title: 'External APIs',
    icon: Code,
    desc: 'GitHub, LeetCode, Codeforces evidence gathering (Layer 2).',
    col: 4,
    row: 2,
    color: 'bg-orange-100 text-orange-600 border-orange-200'
  },
  {
    id: 'llm',
    title: 'LLM Inference',
    icon: Brain,
    desc: 'Groq (Cloud) or Ollama (Local) for candidate reasoning (Layer 3).',
    col: 4,
    row: 3,
    color: 'bg-pink-100 text-pink-600 border-pink-200'
  }
]

export function Architecture() {
  return (
    <section id="architecture" className="bg-cream px-6 py-24 md:px-10 md:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-20">
          <h2 className="font-instrument text-4xl text-ink md:text-5xl">System Architecture</h2>
          <p className="mt-4 text-base text-muted max-w-2xl mx-auto">
            A production-grade, distributed system designed for scalability, security, and high-performance AI inference.
          </p>
        </div>

        <div className="relative w-full overflow-x-auto pb-10">
          <div className="min-w-[900px] grid grid-cols-4 gap-8">
            
            {nodes.map((node, i) => (
              <motion.div
                key={node.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                style={{ gridColumnStart: node.col, gridRowStart: node.row }}
                className="flex flex-col"
              >
                <div className={`flex flex-col items-start p-6 rounded-2xl border bg-white shadow-sm transition-shadow hover:shadow-md relative group`}>
                  <div className={`p-3 rounded-xl border mb-4 ${node.color}`}>
                    <node.icon className="h-6 w-6" />
                  </div>
                  <h3 className="font-instrument text-xl font-medium text-ink">{node.title}</h3>
                  <p className="mt-2 text-sm text-muted">{node.desc}</p>
                </div>
              </motion.div>
            ))}

          </div>
        </div>
      </div>
    </section>
  )
}
