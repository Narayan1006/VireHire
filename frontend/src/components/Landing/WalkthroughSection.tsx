import { motion } from 'framer-motion'
import { LayoutDashboard, Users, User, Settings } from 'lucide-react'

const screens = [
  {
    id: 'dashboard',
    title: 'Recruiter Dashboard',
    icon: LayoutDashboard,
    desc: 'Upload CSV datasets, paste job descriptions, and monitor the real-time progress of the asynchronous AI pipeline.',
    gradient: 'from-blue-500/20 to-purple-500/20'
  },
  {
    id: 'ranking',
    title: 'Candidate Ranking',
    icon: Users,
    desc: 'View the final shortlisted candidates scored across PR metrics, LeetCode performance, and LLM reasoning.',
    gradient: 'from-emerald-500/20 to-teal-500/20'
  },
  {
    id: 'details',
    title: 'Evidence Details',
    icon: User,
    desc: 'Deep dive into a specific candidate to see exactly what GitHub repos and code commits influenced the AI verdict.',
    gradient: 'from-orange-500/20 to-red-500/20'
  },
  {
    id: 'settings',
    title: 'BYOK Settings',
    icon: Settings,
    desc: 'Securely configure personal GitHub tokens and Groq/Ollama API keys with AES-256 encrypted persistence.',
    gradient: 'from-violet-500/20 to-fuchsia-500/20'
  }
]

export function WalkthroughSection() {
  return (
    <section className="bg-cream px-6 py-24 md:px-10 md:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="font-instrument text-4xl text-ink md:text-5xl">Product Walkthrough</h2>
          <p className="mt-4 text-base text-muted max-w-2xl mx-auto">
            A seamless recruiter experience built on top of a highly technical backend.
          </p>
        </div>

        <div className="space-y-24">
          {screens.map((screen, i) => (
            <motion.div
              key={screen.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6 }}
              className={`flex flex-col md:flex-row gap-12 items-center ${i % 2 !== 0 ? 'md:flex-row-reverse' : ''}`}
            >
              {/* Text Content */}
              <div className="w-full md:w-1/3 space-y-4">
                <div className="h-12 w-12 rounded-xl bg-white border border-border flex items-center justify-center shadow-sm text-ink mb-6">
                  <screen.icon className="h-6 w-6" />
                </div>
                <h3 className="font-instrument text-3xl font-medium text-ink">{screen.title}</h3>
                <p className="text-base text-muted leading-relaxed">{screen.desc}</p>
              </div>

              {/* Image/Mockup Container */}
              <div className="w-full md:w-2/3">
                <div className="relative aspect-[16/10] w-full rounded-2xl border border-border/60 bg-white shadow-xl overflow-hidden group">
                  {/* Mockup Top Bar */}
                  <div className="absolute top-0 left-0 right-0 h-10 border-b border-border/50 bg-cream/50 backdrop-blur flex items-center px-4 gap-2 z-10">
                    <div className="h-3 w-3 rounded-full bg-red-400/80"></div>
                    <div className="h-3 w-3 rounded-full bg-amber-400/80"></div>
                    <div className="h-3 w-3 rounded-full bg-emerald-400/80"></div>
                  </div>
                  
                  {/* Mockup Body (Placeholder gradient instead of image) */}
                  <div className={`absolute inset-0 pt-10 bg-gradient-to-br ${screen.gradient} flex items-center justify-center`}>
                    <div className="text-center p-6 bg-white/50 backdrop-blur rounded-xl border border-white/20">
                      <p className="text-sm font-medium text-ink/70">Screenshot Placeholder</p>
                      <p className="text-xs text-ink/50 mt-1">{screen.title} Interface</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
