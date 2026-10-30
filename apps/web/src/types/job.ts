export interface BreakdownComponents {
  external_collaboration?: number | null;
  repo_impact?: number | null;
  sustained_activity?: number | null;
  breadth?: number | null;
  skill_overlap?: number | null;
  leetcode?: number | null;
  [key: string]: number | null | undefined;
}

export interface ScoreBreakdown {
  components?: BreakdownComponents;
  weights?: Record<string, number>;
  w?: number;
  confidence?: number;
  confidence_parts?: { github?: number; leetcode?: number };
  retrieval_norm?: number;
  evidence_score?: number | null;
  final_score?: number;
  label?: string;
  reasons?: string[];
  [key: string]: any;
}

export type CandidateLabel = "strong_match" | "needs_review" | "insufficient_evidence";

export interface JobResultRow {
  rank: number;
  candidate_id: string;
  name: string;
  retrieval_score: number;
  evidence_score?: number | null;
  confidence: number;
  final_score?: number | null;
  label?: CandidateLabel | null;
  snippet: string;
  reasons: string[];
  breakdown: ScoreBreakdown;
}

export interface EvidenceItem {
  source: "github" | "leetcode";
  username?: string | null;
  status: "verified" | "unverified" | "error";
  reason?: string | null;
  fetched_at: string;
  payload: Record<string, any>;
}

export interface CandidateEvidenceRow {
  rank: number;
  candidate_id: string;
  name: string;
  evidence: EvidenceItem[];
}

export interface JobResultsResponse {
  status: string;
  candidate_count: number;
  rows: JobResultRow[];
}

export interface JobEvidenceResponse {
  status: string;
  candidate_count: number;
  rows: CandidateEvidenceRow[];
  candidates?: CandidateEvidenceRow[];
}
