import type { Candidate, DashboardStats } from '../types'

// Empty mock data - will be populated from real API
export const dashboardStats: DashboardStats = {
  totalCandidates: 0,
  avgScore: 0,
  verifiedProfiles: 0,
  timeSaved: '0 hrs',
  verdictBreakdown: { HIRE: 0, REVIEW: 0, REJECT: 0 },
}

// Empty candidates array - will be populated from real API
export const candidates: Candidate[] = []

// No top candidate until real data is loaded
export const topCandidate = null
