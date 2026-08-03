import { motion } from 'framer-motion'
import { ArrowRight, X, Check } from 'lucide-react'

const comparisons = [
  { old: 'Resume Keywords', new: 'Semantic Retrieval', oldDesc: 'Blind regex matching', newDesc: 'Vector-space similarity search' },
  { old: 'Resume Claims', new: 'Evidence Verification', oldDesc: 'Trusting unverified PDFs', newDesc: 'Live GitHub/LeetCode API checks' },
  { old: 'Manual Screening', new: 'Automated Ranking', oldDesc: 'Hours of human sorting', newDesc: 'Asynchronous pipeline processing' },
  { old: 'One-dimensional score', new: 'Three-layer AI decision', oldDesc: 'Simplistic point systems', newDesc: 'RAG + Evidence + LLM reasoning' },
  { old: 'No engineering signals', new: 'GitHub + LeetCode', oldDesc: 'Missing technical context', newDesc: 'Repo analysis & DSA metrics' },
]

export function Comparison() {
  return (
    <section className="bg-white px-6 py-24 md:px-10 md:py-32 border-t border-border">
      <div className="mx-auto max-w-5xl">
        <div className="text-center mb-16">
          <h2 className="font-instrument text-4xl text-ink md:text-5xl">Why VeriHire is Different</h2>
          <p className="mt-4 text-base text-muted max-w-2xl mx-auto">
            Traditional ATS platforms optimize for recruiters. VeriHire optimizes for engineering truth.
          </p>
        </div>

        <div className="card-editorial overflow-hidden bg-white/50 border border-border">
          {/* Header */}
          <div className="grid grid-cols-[1fr_auto_1fr] items-center p-6 border-b border-border bg-cream/30">
            <div className="text-center font-instrument text-xl text-muted">Traditional ATS</div>
            <div className="w-8"></div>
            <div className="text-center font-instrument text-xl text-ink font-medium flex items-center justify-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              VeriHire AI
            </div>
          </div>

          {/* Body */}
          <div className="divide-y divide-border">
            {comparisons.map((item, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="grid grid-cols-[1fr_auto_1fr] items-center p-6 transition-colors hover:bg-cream/10"
              >
                <div className="flex items-center gap-4 justify-end text-right">
                  <div>
                    <div className="text-base font-medium text-muted">{item.old}</div>
                    <div className="text-xs text-muted/60 mt-0.5">{item.oldDesc}</div>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-red-50 flex items-center justify-center shrink-0">
                    <X className="h-4 w-4 text-red-500" />
                  </div>
                </div>

                <div className="w-8 flex justify-center">
                  <ArrowRight className="h-4 w-4 text-border" />
                </div>

                <div className="flex items-center gap-4">
                  <div className="h-8 w-8 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
                    <Check className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div>
                    <div className="text-base font-medium text-ink">{item.new}</div>
                    <div className="text-xs text-emerald-600/70 mt-0.5">{item.newDesc}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
