import { motion } from 'framer-motion'

const metrics = [
  { value: '3-Layer', label: 'AI Inference Pipeline', desc: 'RAG Retrieval, Evidence Verification, and LLM Reasoning.' },
  { value: 'Async', label: 'Processing Architecture', desc: 'Non-blocking I/O orchestration via Spring Boot @Async.' },
  { value: 'AES-256', label: 'GCM Encryption', desc: 'Zero-knowledge credential storage for BYOK configuration.' },
  { value: 'Vector', label: 'Semantic Embeddings', desc: 'High-dimensional similarity search via ChromaDB.' },
]

export function Performance() {
  return (
    <section className="bg-ink px-6 py-24 md:px-10 md:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-16">
          {metrics.map((metric, i) => (
            <motion.div
              key={metric.value}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="flex flex-col border-l border-white/20 pl-6"
            >
              <div className="font-instrument text-5xl font-medium text-cream mb-2">{metric.value}</div>
              <div className="text-base font-semibold text-white/90 tracking-wide mb-3">{metric.label}</div>
              <p className="text-sm text-white/50 leading-relaxed">{metric.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
