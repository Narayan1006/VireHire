import React from "react";
import { EvidenceItem } from "@/types/job";
import { Star, GitPullRequest, FolderGit2 } from "lucide-react";

export const GitHubIcon: React.FC<{ className?: string }> = ({ className = "h-3.5 w-3.5" }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
    />
  </svg>
);

export const LeetCodeIcon: React.FC<{ className?: string }> = ({ className = "h-3.5 w-3.5" }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    aria-hidden="true"
  >
    <path d="M16.102 17.93l-2.697 2.607c-.466.467-1.111.662-1.823.662s-1.357-.195-1.824-.662l-4.332-4.363c-.467-.467-.702-1.15-.702-1.863s.235-1.357.702-1.824l4.319-4.38c.467-.467 1.125-.645 1.837-.645s1.357.195 1.823.662l2.697 2.606c.514.515 1.365.497 1.9-.038.535-.536.553-1.387.039-1.901l-2.609-2.636a5.226 5.226 0 00-3.85-1.442c-1.492 0-2.903.58-3.957 1.634L3.307 10.457c-1.054 1.055-1.634 2.466-1.634 3.958 0 1.493.58 2.904 1.634 3.958l4.332 4.364c1.054 1.054 2.465 1.634 3.957 1.634s2.904-.58 3.958-1.634l2.608-2.636c.514-.514.496-1.365-.039-1.901-.535-.535-1.386-.553-1.9-.038z" />
    <path d="M20.811 13.01H10.666c-.742 0-1.344.602-1.344 1.344s.602 1.344 1.344 1.344h10.145c.742 0 1.344-.602 1.344-1.344s-.602-1.344-1.344-1.344z" fill="#FFA116" />
  </svg>
);

interface EvidenceChipsProps {
  evidence?: EvidenceItem[];
}

export const EvidenceChips: React.FC<EvidenceChipsProps> = ({
  evidence = [],
}) => {
  const githubEvidence = evidence.find((e) => e.source === "github");
  const leetcodeEvidence = evidence.find((e) => e.source === "leetcode");

  if (!githubEvidence && !leetcodeEvidence) {
    return (
      <span className="inline-flex items-center text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
        No public profiles
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {/* GitHub Chip */}
      {githubEvidence && (
        <div
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs transition-colors border ${
            githubEvidence.status === "verified"
              ? "bg-slate-900 text-white border-slate-800 hover:bg-slate-800"
              : "bg-slate-100 text-slate-600 border-slate-200"
          }`}
          title={
            githubEvidence.status === "verified"
              ? `Verified GitHub: @${githubEvidence.username}`
              : `GitHub Unverified: ${githubEvidence.reason || "no proof"}`
          }
        >
          <GitHubIcon className="h-3 w-3 shrink-0" />
          {githubEvidence.status === "verified" ? (
            <div className="flex items-center gap-1.5 font-medium">
              <span>@{githubEvidence.username}</span>
              {/* Stars badge */}
              {githubEvidence.payload?.total_stars > 0 && (
                <span className="flex items-center gap-0.5 text-[11px] text-amber-300 font-normal">
                  <Star className="h-2.5 w-2.5 fill-amber-300 text-amber-300" />
                  {githubEvidence.payload.total_stars}
                </span>
              )}
              {/* PRs badge */}
              {githubEvidence.payload?.merged_external_prs > 0 && (
                <span className="flex items-center gap-0.5 text-[11px] text-emerald-300 font-normal">
                  <GitPullRequest className="h-2.5 w-2.5" />
                  {githubEvidence.payload.merged_external_prs} PRs
                </span>
              )}
              {/* Repos badge */}
              {githubEvidence.payload?.public_repos_count > 0 && (
                <span className="flex items-center gap-0.5 text-[11px] text-slate-300 font-normal">
                  <FolderGit2 className="h-2.5 w-2.5" />
                  {githubEvidence.payload.public_repos_count}
                </span>
              )}
            </div>
          ) : (
            <span className="text-[11px] text-slate-500 font-normal">
              {githubEvidence.reason === "no_token"
                ? "No token"
                : githubEvidence.reason === "not_found"
                ? "Not found"
                : "Unverified"}
            </span>
          )}
        </div>
      )}

      {/* LeetCode Chip */}
      {leetcodeEvidence && (
        <div
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs transition-colors border ${
            leetcodeEvidence.status === "verified"
              ? "bg-amber-50 text-amber-900 border-amber-200"
              : "bg-slate-100 text-slate-600 border-slate-200"
          }`}
          title={
            leetcodeEvidence.status === "verified"
              ? `Verified LeetCode: @${leetcodeEvidence.username} (${leetcodeEvidence.payload?.total_solved || 0} solved)`
              : `LeetCode Unverified: ${leetcodeEvidence.reason || "no profile"}`
          }
        >
          <LeetCodeIcon className="h-3 w-3 shrink-0" />
          {leetcodeEvidence.status === "verified" ? (
            <div className="flex items-center gap-1 font-medium">
              <span>{leetcodeEvidence.payload?.total_solved ?? 0} solved</span>
              {leetcodeEvidence.payload?.contest_rating && (
                <span className="text-[10px] text-amber-700 bg-amber-100/70 px-1 rounded">
                  {Math.round(leetcodeEvidence.payload.contest_rating)}★
                </span>
              )}
            </div>
          ) : (
            <span className="text-[11px] text-slate-500 font-normal">
              {leetcodeEvidence.reason === "not_found" ? "Not found" : "Unverified"}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
