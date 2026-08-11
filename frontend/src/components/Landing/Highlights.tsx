import { motion } from 'framer-motion'
import { Lock, Network, Database, RefreshCw, Search, BrainCircuit, Key, FileJson, Laptop, CheckCircle2 } from 'lucide-react'

const features = [
  { icon: Network, title: 'Spring Boot REST APIs', desc: 'Robust API layer built with Spring Boot 3.3, utilizing MVC patterns, DTOs, and global exception handling.' },
  { icon: Lock, title: 'JWT Authentication', desc: 'Stateless authentication via Spring Security with RSA-signed JSON Web Tokens and BCrypt password hashing.' },
  { icon: Laptop, title: 'Python AI Microservice', desc: 'FastAPI backend decoupled from the monolith to handle heavy asynchronous inference tasks efficiently.' },
  { icon: RefreshCw, title: 'Asynchronous Processing', desc: 'Background job orchestration using Spring @Async, preventing timeout issues on long LLM inference calls.' },
  { icon: Database, title: 'Neon PostgreSQL', desc: 'Relational data modeling for Users, Jobs, and encrypted Settings, managed with Hibernate JPA.' },
  { icon: Box, title: 'Docker Compose', desc: 'Containerized infrastructure for seamless orchestration of the frontend, backend, and ChromaDB vector store.' }, // Note: we'll import Box
  { icon: FileJson, title: 'Swagger OpenAPI', desc: 'Auto-generated API documentation for both Spring Boot and FastAPI, facilitating clean client code generation.' },
  { icon: Database, title: 'CSV Candidate Processing', desc: 'Scalable multipart file ingestion and pandas dataframe processing for large resume datasets.' },
  { icon: CheckCircle2, title: 'Evidence Verification', desc: 'Deterministic validation of candidate claims against live developer profiles to prevent hallucinated scores.' },
  { icon: Search, title: 'Semantic Retrieval', desc: 'Sentence-transformers embeddings indexed in ChromaDB for high-speed k-NN similarity search.' },
  { icon: BrainCircuit, title: 'LLM Reasoning', desc: 'Llama 3 inference pipelines deployed via Groq (cloud) or Ollama (local) with strict temperature control.' },
  { icon: Key, title: 'BYOK Architecture', desc: 'Bring-Your-Own-Keys model with AES-256-GCM encrypted persistence in the database layer.' }
]

import { Box } from 'lucide-react' // Fixing import

export function Highlights() {
  return (
    <section className="bg-cream px-6 py-24 md:px-10 md:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="font-instrument text-4xl text-ink md:text-5xl">Engineering Highlights</h2>
          <p className="mt-4 text-base text-muted max-w-2xl mx-auto">
            A deep dive into the technical capabilities and patterns implemented across the stack.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feat, i) => (
            <motion.div
              key={feat.title}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: (i % 3) * 0.1 }}
              className="group flex gap-4 p-5 rounded-2xl border border-border/60 bg-white/50 transition-colors hover:bg-white hover:border-border"
            >
              <div className="shrink-0 mt-1">
                <feat.icon className="h-5 w-5 text-muted transition-colors group-hover:text-ink" />
              </div>
              <div>
                <h3 className="font-medium text-ink text-base mb-1">{feat.title}</h3>
                <p className="text-sm text-muted leading-relaxed">{feat.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
