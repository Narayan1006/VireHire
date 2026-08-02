export type Verdict = 'HIRE' | 'REVIEW' | 'REJECT'

export interface Candidate {
  id: string
  rank: number
  name: string
  percentile: number
  prScore: number
  github: number
  dsa: number
  verdict: Verdict
  email: string
  role: string
  skills: SkillConfidence[]
  githubEvidence: GitHubEvidence
  leetcode: LeetCodeStats
  timeline: TimelineEntry[]
  riskFlags: RiskFlag[]
  summary: string
}

export interface SkillConfidence {
  name: string
  claimed: number
  verified: number
}

export interface GitHubEvidence {
  repoCount: number
  languages: { name: string; percentage: number }[]
  architectureScore: number
  aiUsageLevel: 'Low' | 'Medium' | 'High'
  lastActive: string
  verified: boolean
}

export interface LeetCodeStats {
  rating: number
  problemsSolved: number
  consistency: number
  easy: number
  medium: number
  hard: number
}

export interface TimelineEntry {
  id: string
  type: 'experience' | 'education'
  title: string
  organization: string
  period: string
  description?: string
}

export interface RiskFlag {
  id: string
  severity: 'low' | 'medium' | 'high'
  label: string
  description: string
}

export interface DashboardStats {
  totalCandidates: number
  avgScore: number
  verifiedProfiles: number
  timeSaved: string
  verdictBreakdown: { HIRE: number; REVIEW: number; REJECT: number }
}
