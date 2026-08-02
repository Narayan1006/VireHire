import { motion } from 'framer-motion'
import type { SkillConfidence } from '../../types'

export function SkillBars({ skills }: { skills: SkillConfidence[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-editorial p-6"
    >
      <h2 className="font-instrument text-xl text-ink">Skill Confidence</h2>
      <p className="mt-1 text-sm text-muted">Claimed vs verified proficiency</p>

      <div className="mt-6 space-y-5">
        {skills.map((skill) => {
          const verified = skill.verified >= skill.claimed - 10
          return (
            <div key={skill.name}>
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-ink">{skill.name}</span>
                <span
                  className={
                    verified ? 'text-emerald-700' : 'text-red-600'
                  }
                >
                  {verified ? 'Verified' : 'Unverified'}
                </span>
              </div>
              <div className="relative h-3 overflow-hidden rounded-full bg-border">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-red-200"
                  style={{ width: `${skill.claimed}%` }}
                />
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-emerald-500"
                  style={{ width: `${skill.verified}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-xs text-muted">
                <span>Claimed {skill.claimed}%</span>
                <span>Verified {skill.verified}%</span>
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
