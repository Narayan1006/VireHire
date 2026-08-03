import { motion } from 'framer-motion'
import { Layers, Search, Code2, Brain } from 'lucide-react'

const layers = [
  {
    num: '01',
    title: 'Semantic Retrieval',
    icon: Search,
    color: 'text-violet-600',
    bg: 'bg-violet-100',
    border: 'border-violet-200',
    desc: 'Uses vector embeddings and ChromaDB to perform semantic search across resumes, filtering out candidates that do not meet the core job requirements before wasting expensive LLM tokens.'
  },
  {
    num: '02',
    title: 'Evidence Verification',
    icon: Code2,
    color: 'text-orange-600',
    bg: 'bg-orange-100',
    border: 'border-orange-200',
    desc: 'Verifies resume claims by querying the GitHub, LeetCode, and Codeforces APIs. Extracts real engineering signals like repository count, commit activity, language distribution, and DSA problem-solving capabilities.'
  },
  {
    num: '03',
    title: 'LLM Reasoning',
    icon: Brain,
    color: 'text-pink-600',
    bg: 'bg-pink-100',
    border: 'border-pink-200',
    desc: 'Uses a large language model (Llama 3 via Groq or Ollama) to synthesize the raw evidence and the resume data. Produces recruiter-friendly summaries and issues a final HIRE, REVIEW, or REJECT recommendation.'
  }
]

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.2 }
  }
}

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  show: {
    opacity: 1, 
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' as const }
  }
}

export function Pipeline() {
  return (
    <section id="pipeline" className="bg-white px-6 py-24 md:px-10 md:py-32 border-t border-border">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col md:flex-row items-center gap-4 mb-20 text-center md:text-left">
          <div className="p-4 bg-ink rounded-2xl text-cream shrink-0">
            <Layers className="h-8 w-8" />
          </div>
          <div>
            <h2 className="font-instrument text-4xl text-ink md:text-5xl">Three-Layer AI Pipeline</h2>
            <p className="mt-4 text-base text-muted max-w-2xl">
              We replace keyword-matching with a deterministic, multi-stage data pipeline to uncover true engineering ability.
            </p>
          </div>
        </div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8"
        >
          {layers.map((layer) => (
            <motion.div 
              key={layer.num}
              variants={cardVariants}
              whileHover={{ y: -8 }}
              className={`flex flex-col p-8 rounded-3xl border bg-white shadow-sm transition-all hover:shadow-xl`}
            >
              <div className="flex items-center justify-between mb-6">
                <span className="font-instrument text-4xl text-muted/30">{layer.num}</span>
                <div className={`p-4 rounded-2xl border ${layer.bg} ${layer.color} ${layer.border}`}>
                  <layer.icon className="h-6 w-6" />
                </div>
              </div>
              <h3 className="font-instrument text-2xl font-medium text-ink mb-4">{layer.title}</h3>
              <p className="text-muted leading-relaxed flex-1">{layer.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
