import { motion } from 'framer-motion'
import { Code, Database, Server, Box, Layout, Shield, Cpu, Cloud, Zap, ArrowRight, BookMarked, Terminal } from 'lucide-react'
import { GitHubIcon } from '../ui/SocialIcons'

const stack = [
  { name: 'React', icon: Layout, color: 'text-sky-500' },
  { name: 'TypeScript', icon: Code, color: 'text-blue-600' },
  { name: 'Spring Boot', icon: Server, color: 'text-green-600' },
  { name: 'Spring Security', icon: Shield, color: 'text-emerald-700' },
  { name: 'JWT', icon: Key, color: 'text-purple-600' },
  { name: 'Neon PostgreSQL', icon: Database, color: 'text-teal-500' },
  { name: 'Python', icon: Terminal, color: 'text-yellow-600' },
  { name: 'FastAPI', icon: Zap, color: 'text-teal-600' },
  { name: 'ChromaDB', icon: Box, color: 'text-orange-500' },
  { name: 'Docker', icon: Cloud, color: 'text-blue-500' },
  { name: 'Swagger', icon: BookMarked, color: 'text-green-500' },
  { name: 'GitHub API', icon: GitHubIcon, color: 'text-zinc-800' },
  { name: 'Groq', icon: Cpu, color: 'text-red-500' },
  { name: 'Ollama', icon: Cpu, color: 'text-zinc-600' },
  { name: 'Framer Motion', icon: ArrowRight, color: 'text-fuchsia-500' },
]

import { Key } from 'lucide-react'

export function TechStack() {
  return (
    <section className="bg-white px-6 py-24 md:px-10 md:py-32 overflow-hidden border-t border-border">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="font-instrument text-4xl text-ink md:text-5xl">Technology Stack</h2>
          <p className="mt-4 text-base text-muted max-w-2xl mx-auto">
            Built on a modern, typed, and containerized foundation for high performance.
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-4 max-w-4xl mx-auto">
          {stack.map((tech, i) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: (i % 5) * 0.1 }}
              whileHover={{ y: -4, scale: 1.05 }}
              className="flex items-center gap-3 px-5 py-3 rounded-xl border border-border/60 bg-cream/30 shadow-sm cursor-default"
            >
              <tech.icon className={`h-5 w-5 ${tech.color}`} />
              <span className="font-medium text-ink text-sm">{tech.name}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
