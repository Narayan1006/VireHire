import React, { useEffect } from "react";
import { JobResultRow, EvidenceItem } from "@/types/job";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  X,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Star,
  GitPullRequest,
  FolderGit2,
  Layers,
  Sparkles,
  TrendingUp,
  ShieldCheck,
  FileText,
  BarChart3,
} from "lucide-react";
import { GitHubIcon, LeetCodeIcon } from "./EvidenceChips";

interface ScoreBreakdownDrawerProps {
  candidate: JobResultRow | null;
  evidence?: EvidenceItem[];
  jobTitle?: string;
  onClose: () => void;
}

export const ScoreBreakdownDrawer: React.FC<ScoreBreakdownDrawerProps> = ({
  candidate,
  evidence = [],
  jobTitle,
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!candidate) return null;

  const { breakdown, reasons = [] } = candidate;
  const components = breakdown.components || {};
  const weights = breakdown.weights || {};
  const confidence = breakdown.confidence ?? candidate.confidence ?? 0;
  const confParts = breakdown.confidence_parts || { github: 0, leetcode: 0 };
  const w = breakdown.w ?? (0.4 * confidence);
  const retrievalNorm = breakdown.retrieval_norm ?? candidate.retrieval_score ?? 0;
  const evidenceScore = candidate.evidence_score ?? breakdown.evidence_score ?? null;
  const finalScore = candidate.final_score ?? breakdown.final_score ?? candidate.retrieval_score;

  const githubEvidence = evidence.find((e) => e.source === "github");
  const leetcodeEvidence = evidence.find((e) => e.source === "leetcode");

  const getLabelBadge = (label?: string | null) => {
    switch (label) {
      case "strong_match":
        return (
          <Badge variant="outline" className="bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold px-2.5 py-1">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 mr-1" />
            Strong Match
          </Badge>
        );
      case "needs_review":
        return (
          <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 font-semibold px-2.5 py-1">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600 mr-1" />
            Needs Review
          </Badge>
        );
      case "insufficient_evidence":
      default:
        return (
          <Badge variant="outline" className="bg-slate-100 text-slate-700 border-slate-300 font-medium px-2.5 py-1">
            <HelpCircle className="h-3.5 w-3.5 text-slate-500 mr-1" />
            Insufficient Evidence
          </Badge>
        );
    }
  };

  const signalDefinitions = [
    {
      key: "external_collaboration",
      title: "External Collaboration",
      desc: "Merged PRs & code reviews to third-party repos",
      score: components.external_collaboration,
      weight: weights.external_collaboration ?? 0.25,
      icon: <GitPullRequest className="h-4 w-4 text-emerald-600" />,
    },
    {
      key: "repo_impact",
      title: "Repository Impact",
      desc: "Log-saturated stars received, forks, followers",
      score: components.repo_impact,
      weight: weights.repo_impact ?? 0.25,
      icon: <Star className="h-4 w-4 text-amber-500" />,
    },
    {
      key: "sustained_activity",
      title: "Sustained Activity",
      desc: "Annual commits, push recency & account age",
      score: components.sustained_activity,
      weight: weights.sustained_activity ?? 0.20,
      icon: <TrendingUp className="h-4 w-4 text-blue-600" />,
    },
    {
      key: "breadth",
      title: "Code Breadth",
      desc: "Distinct programming languages & public repos",
      score: components.breadth,
      weight: weights.breadth ?? 0.15,
      icon: <FolderGit2 className="h-4 w-4 text-indigo-600" />,
    },
    {
      key: "skill_overlap",
      title: "Job Skill Overlap",
      desc: "Demonstrated tech matching job requirements",
      score: components.skill_overlap,
      weight: weights.skill_overlap ?? 0.15,
      icon: <Sparkles className="h-4 w-4 text-purple-600" />,
    },
    {
      key: "leetcode",
      title: "Problem Solving (LeetCode)",
      desc: "Solved problems weighted by difficulty & rating",
      score: components.leetcode,
      weight: weights.leetcode ?? null,
      icon: <LeetCodeIcon className="h-4 w-4 text-amber-600" />,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end transition-opacity">
      {/* Click backdrop to close */}
      <div className="absolute inset-0" onClick={onClose} aria-label="Close modal backdrop" />

      {/* Drawer Container */}
      <div className="relative w-full max-w-2xl bg-white shadow-2xl h-full flex flex-col z-10 overflow-hidden animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="px-6 py-5 border-b border-slate-200 flex items-start justify-between bg-slate-50/70">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-slate-200 text-xs font-bold text-slate-700 font-mono">
                #{candidate.rank}
              </span>
              <h2 className="text-xl font-bold text-slate-900">{candidate.name}</h2>
              {getLabelBadge(candidate.label)}
            </div>
            {jobTitle && (
              <p className="text-xs text-slate-500">
                Evaluation for position: <span className="font-medium text-slate-700">{jobTitle}</span>
              </p>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-200"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Drawer Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* Hero Formula & Score Breakdown */}
          <div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-indigo-100/80 pb-4">
              <div>
                <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wider">
                  Deterministic Final Score
                </span>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-3xl font-extrabold text-slate-900">
                    {(finalScore * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    (raw: {finalScore.toFixed(4)})
                  </span>
                </div>
              </div>

              {/* Confidence badge */}
              <div className="text-right">
                <span className="text-xs font-medium text-slate-500">Verified Proof Confidence</span>
                <div className="flex items-center justify-end gap-1.5 mt-0.5">
                  <ShieldCheck className={`h-4 w-4 ${confidence >= 0.5 ? "text-emerald-600" : confidence > 0.2 ? "text-amber-500" : "text-slate-400"}`} />
                  <span className="text-lg font-bold text-slate-800">
                    {(confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  GH: {((confParts.github ?? 0) * 100).toFixed(0)}% • LC: {((confParts.leetcode ?? 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Formula display */}
            <div className="rounded-lg bg-white border border-slate-200/80 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
                <span>Deterministic Scoring Formula:</span>
                <span className="font-mono text-[11px] text-indigo-600 font-semibold">
                  (1 - w) · retrieval + w · evidence
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center pt-1 font-mono text-xs">
                <div className="p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Retrieval Norm</div>
                  <div className="text-sm font-bold text-slate-800 mt-0.5">
                    {(retrievalNorm * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-500">weight: {((1 - w) * 100).toFixed(1)}%</div>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Evidence Weight (w)</div>
                  <div className="text-sm font-bold text-indigo-700 mt-0.5">
                    {(w * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-500">0.4 × {(confidence * 100).toFixed(0)}% conf</div>
                </div>

                <div className="p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Evidence Score</div>
                  <div className="text-sm font-bold text-slate-800 mt-0.5">
                    {evidenceScore !== null ? `${(evidenceScore * 100).toFixed(1)}%` : "None"}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {evidenceScore !== null ? `weight: ${(w * 100).toFixed(1)}%` : "no penalty"}
                  </div>
                </div>
              </div>

              {evidenceScore === null && (
                <p className="text-[11px] text-slate-500 italic text-center pt-1">
                  Notice: No verified evidence found. Per spec, candidate is scored exactly on retrieval baseline (w = 0) without penalty.
                </p>
              )}
            </div>
          </div>

          {/* Factual Proof Points (Data-Derived Reasons) */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-xs">
                Verified Factual Proof Points
              </h3>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
              {reasons.length > 0 ? (
                <ul className="space-y-2">
                  {reasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-700">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{reason}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-400 italic">No specific proof points generated.</p>
              )}
            </div>
          </div>

          {/* Multi-Signal Evidence Components Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-xs">
                  Evidence Signal Components
                </h3>
              </div>
              <span className="text-[11px] text-slate-400">Provisional Weights (M3)</span>
            </div>

            <div className="space-y-2">
              {signalDefinitions.map((sig) => {
                const hasScore = sig.score !== null && sig.score !== undefined;
                const scorePercent = hasScore ? Math.round(sig.score! * 100) : null;

                return (
                  <div
                    key={sig.key}
                    className={`rounded-lg border p-3 transition-colors ${
                      hasScore
                        ? "border-slate-200 bg-white hover:border-slate-300"
                        : "border-dashed border-slate-200 bg-slate-50/50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <div className="p-1.5 rounded-md bg-slate-100">{sig.icon}</div>
                        <div>
                          <div className="text-xs font-semibold text-slate-900 flex items-center gap-2">
                            <span>{sig.title}</span>
                            {sig.weight !== null && (
                              <span className="text-[10px] text-slate-400 font-mono font-normal">
                                (weight: {Math.round(sig.weight * 100)}%)
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-500">{sig.desc}</p>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        {hasScore ? (
                          <span className="text-sm font-bold text-slate-900 font-mono">
                            {scorePercent}%
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Unverified</span>
                        )}
                      </div>
                    </div>

                    {hasScore && (
                      <div className="mt-2.5 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                          style={{ width: `${Math.min(100, Math.max(0, scorePercent!))}%` }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Raw Verified Sources Inspection */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-xs">
              Verified Public Profiles & Cache
            </h3>

            <div className="space-y-3">
              {/* GitHub Card */}
              {githubEvidence ? (
                <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <GitHubIcon className="h-4 w-4 text-slate-900" />
                      <span className="text-xs font-bold text-slate-900">GitHub Profile</span>
                      {githubEvidence.status === "verified" ? (
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                          Verified
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-200 text-[10px]">
                          {githubEvidence.reason || "Unverified"}
                        </Badge>
                      )}
                    </div>

                    {githubEvidence.username && (
                      <a
                        href={`https://github.com/${githubEvidence.username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                      >
                        <span>@{githubEvidence.username}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>

                  {githubEvidence.status === "verified" && githubEvidence.payload && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs pt-1">
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-slate-400">Stars</div>
                        <div className="text-sm font-bold text-slate-800">{githubEvidence.payload.total_stars ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-slate-400">Merged PRs</div>
                        <div className="text-sm font-bold text-slate-800">{githubEvidence.payload.merged_external_prs ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-slate-400">Commits (1y)</div>
                        <div className="text-sm font-bold text-slate-800">{githubEvidence.payload.commit_contributions ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-slate-400">Public Repos</div>
                        <div className="text-sm font-bold text-slate-800">{githubEvidence.payload.public_repos_count ?? 0}</div>
                      </div>
                    </div>
                  )}

                  {/* Languages histogram */}
                  {githubEvidence.payload?.languages_histogram && Object.keys(githubEvidence.payload.languages_histogram).length > 0 && (
                    <div className="pt-2">
                      <span className="text-[11px] font-semibold text-slate-600 block mb-1">Demonstrated Languages:</span>
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(githubEvidence.payload.languages_histogram).map((lang) => (
                          <span
                            key={lang}
                            className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-700 border border-slate-200"
                          >
                            {lang}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                    <span>Fetched: {new Date(githubEvidence.fetched_at).toLocaleString()}</span>
                    <span>Cached 7-day TTL</span>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 p-4 text-xs text-slate-400 text-center">
                  No GitHub profile linked or verified for this candidate.
                </div>
              )}

              {/* LeetCode Card */}
              {leetcodeEvidence ? (
                <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <LeetCodeIcon className="h-4 w-4 text-amber-600" />
                      <span className="text-xs font-bold text-slate-900">LeetCode Profile</span>
                      {leetcodeEvidence.status === "verified" ? (
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                          Verified
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-200 text-[10px]">
                          {leetcodeEvidence.reason || "Unverified"}
                        </Badge>
                      )}
                    </div>

                    {leetcodeEvidence.username && (
                      <a
                        href={`https://leetcode.com/u/${leetcodeEvidence.username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 font-medium"
                      >
                        <span>@{leetcodeEvidence.username}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>

                  {leetcodeEvidence.status === "verified" && leetcodeEvidence.payload && (
                    <div className="grid grid-cols-4 gap-2 text-center text-xs pt-1">
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-slate-400">Total Solved</div>
                        <div className="text-sm font-bold text-slate-800">{leetcodeEvidence.payload.total_solved ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-emerald-600 font-semibold">Easy</div>
                        <div className="text-sm font-bold text-slate-800">{leetcodeEvidence.payload.easy_solved ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-amber-600 font-semibold">Medium</div>
                        <div className="text-sm font-bold text-slate-800">{leetcodeEvidence.payload.medium_solved ?? 0}</div>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <div className="text-[10px] text-rose-600 font-semibold">Hard</div>
                        <div className="text-sm font-bold text-slate-800">{leetcodeEvidence.payload.hard_solved ?? 0}</div>
                      </div>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                    <span>Fetched: {new Date(leetcodeEvidence.fetched_at).toLocaleString()}</span>
                    <span>Public Best-Effort Cache</span>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 p-4 text-xs text-slate-400 text-center">
                  No LeetCode profile linked or verified for this candidate.
                </div>
              )}
            </div>
          </div>

          {/* Resume Snippet Box */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-400" />
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-xs">
                Resume Content Snippet
              </h3>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 leading-relaxed max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
              {candidate.snippet || "No resume text available."}
            </div>
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/70 flex items-center justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close Breakdown
          </Button>
        </div>
      </div>
    </div>
  );
};
