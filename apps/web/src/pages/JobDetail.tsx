import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  ArrowLeft,
  Calendar,
  Edit3,
  Trash2,
  AlertCircle,
  CheckCircle2,
  UploadCloud,
  FileText,
  Play,
  RotateCw,
  Download,
  Users,
  Search,
  ShieldCheck,
  Sliders,
  ChevronRight,
  HelpCircle,
} from "lucide-react";
import { Job } from "@/pages/JobsList";
import {
  JobResultRow,
  JobResultsResponse,
  EvidenceItem,
  JobEvidenceResponse,
} from "@/types/job";
import { EvidenceChips } from "@/components/EvidenceChips";
import { ScoreBreakdownDrawer } from "@/components/ScoreBreakdownDrawer";

interface RejectionDetail {
  row_number: number;
  reason: string;
}

interface IngestionReport {
  rows_accepted: number;
  rows_rejected: RejectionDetail[];
}

export const JobDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Job state
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saving, setSaving] = useState(false);

  // Delete state
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Candidate & Results state
  const [candidateCount, setCandidateCount] = useState<number>(0);
  const [results, setResults] = useState<JobResultRow[]>([]);
  const [evidenceMap, setEvidenceMap] = useState<Record<string, EvidenceItem[]>>({});
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<JobResultRow | null>(null);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadReport, setUploadReport] = useState<IngestionReport | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Background action states
  const [runLoading, setRunLoading] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const [verifyLoading, setVerifyLoading] = useState(false);
  const [scoreLoading, setScoreLoading] = useState(false);

  // Polling ref & counter
  const pollCountRef = useRef(0);
  const MAX_POLLS = 60; // 60 * 2s = 120s timeout

  const fetchJobAndResults = async (silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    try {
      const jobData = await apiRequest<Job>(`/jobs/${id}`);
      setJob(jobData);
      setEditTitle(jobData.title);
      setEditDescription(jobData.description);

      // Fetch results & candidate count
      try {
        const [resultsData, evidenceData] = await Promise.all([
          apiRequest<JobResultsResponse>(`/jobs/${id}/results`),
          apiRequest<JobEvidenceResponse>(`/jobs/${id}/evidence`).catch(() => null),
        ]);

        setCandidateCount(resultsData.candidate_count);
        setResults(resultsData.rows || []);
        setResultsError(null);

        if (evidenceData && evidenceData.rows) {
          const map: Record<string, EvidenceItem[]> = {};
          for (const row of evidenceData.rows) {
            map[row.candidate_id] = row.evidence || [];
          }
          setEvidenceMap(map);
        }
      } catch (err: any) {
        setResultsError(err.message || "Failed to load candidate results.");
      }
    } catch (err: any) {
      if (!silent) setError(err.message || "Failed to load job details.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobAndResults();
  }, [id]);

  // Polling mechanism when job is in "processing" state
  useEffect(() => {
    if (!id || job?.status !== "processing") {
      pollCountRef.current = 0;
      return;
    }

    const interval = setInterval(async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > MAX_POLLS) {
        clearInterval(interval);
        setRunError("Processing timed out after 2 minutes. Please refresh the page.");
        return;
      }

      try {
        const jobData = await apiRequest<Job>(`/jobs/${id}`);
        setJob(jobData);

        if (jobData.status !== "processing") {
          clearInterval(interval);
          // Refresh results & evidence
          setResultsLoading(true);
          try {
            const [resultsData, evidenceData] = await Promise.all([
              apiRequest<JobResultsResponse>(`/jobs/${id}/results`),
              apiRequest<JobEvidenceResponse>(`/jobs/${id}/evidence`).catch(() => null),
            ]);
            setCandidateCount(resultsData.candidate_count);
            setResults(resultsData.rows || []);
            if (evidenceData && evidenceData.rows) {
              const map: Record<string, EvidenceItem[]> = {};
              for (const row of evidenceData.rows) {
                map[row.candidate_id] = row.evidence || [];
              }
              setEvidenceMap(map);
            }
          } catch {
            // ignore
          } finally {
            setResultsLoading(false);
          }

          if (jobData.status === "done") {
            setSuccessMsg("Processing and scoring completed successfully!");
            setTimeout(() => setSuccessMsg(null), 5000);
          }
        }
      } catch {
        // Ignore single poll failures
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [id, job?.status]);

  const handleFileSelect = (file: File) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setUploadError("Please select a valid CSV file (.csv).");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setUploadError("File exceeds the maximum 5 MB upload limit.");
      return;
    }

    setUploadError(null);
    setUploadReport(null);

    // If candidates already exist, prompt for replacement confirmation
    if (candidateCount > 0) {
      setPendingFile(file);
      setShowReplaceConfirm(true);
    } else {
      executeUpload(file, false);
    }
  };

  const executeUpload = async (file: File, replace: boolean) => {
    if (!id) return;
    setUploading(true);
    setUploadError(null);
    setUploadReport(null);
    setShowReplaceConfirm(false);
    setPendingFile(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const report = await apiRequest<IngestionReport>(
        `/jobs/${id}/candidates?replace=${replace ? "true" : "false"}`,
        {
          method: "POST",
          body: formData,
        }
      );

      setUploadReport(report);
      setCandidateCount(report.rows_accepted);
      setSuccessMsg(`Uploaded ${report.rows_accepted} candidate${report.rows_accepted === 1 ? "" : "s"} successfully.`);
      setTimeout(() => setSuccessMsg(null), 5000);

      // Refresh job state (transitions draft -> processing -> draft while embedding)
      fetchJobAndResults(true);
    } catch (err: any) {
      if (err.status === 409) {
        if (err.message && err.message.toLowerCase().includes("another job is running")) {
          setUploadError("Another job is currently running on the server. Please try again shortly.");
        } else if (err.message && err.message.toLowerCase().includes("already exist")) {
          setPendingFile(file);
          setShowReplaceConfirm(true);
        } else {
          setUploadError(err.message || "Conflict: Unable to upload candidates.");
        }
      } else {
        const rejections =
          err.data?.detail?.rejections ||
          (Array.isArray(err.data?.rejections) ? err.data.rejections : null);
        if (rejections && rejections.length > 0) {
          setUploadReport({
            rows_accepted: 0,
            rows_rejected: rejections,
          });
        }
        setUploadError(err.message || "Failed to upload candidate CSV.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleRunRetrieval = async () => {
    if (!id) return;
    setRunLoading(true);
    setRunError(null);
    setRunMessage(null);

    try {
      await apiRequest<{ detail: string; status: string }>(`/jobs/${id}/run`, {
        method: "POST",
      });

      setRunMessage("Hybrid retrieval matching started. Polling for results...");
      setJob((prev) => (prev ? { ...prev, status: "processing", error: null } : null));
    } catch (err: any) {
      if (err.status === 409) {
        if (err.message && err.message.toLowerCase().includes("another job is running")) {
          setRunError("Another job is currently running on the server. Please try again shortly.");
        } else {
          setRunError(err.message || "Unable to run retrieval right now.");
        }
      } else {
        setRunError(err.message || "Failed to initiate retrieval.");
      }
    } finally {
      setRunLoading(false);
    }
  };

  const handleVerifyEvidence = async () => {
    if (!id) return;
    setVerifyLoading(true);
    setRunError(null);
    setRunMessage(null);

    try {
      await apiRequest<{ detail: string; status: string }>(`/jobs/${id}/verify`, {
        method: "POST",
      });

      setRunMessage("Collecting GitHub & LeetCode evidence in background. Candidates will be re-scored automatically...");
      setJob((prev) => (prev ? { ...prev, status: "processing", error: null } : null));
    } catch (err: any) {
      if (err.status === 409) {
        setRunError(err.message || "Job is already processing or has no rankings.");
      } else {
        setRunError(err.message || "Failed to initiate evidence verification.");
      }
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleRecalculateScores = async () => {
    if (!id) return;
    setScoreLoading(true);
    setRunError(null);

    try {
      const res = await apiRequest<{ detail: string; candidates_scored: number }>(`/jobs/${id}/score`, {
        method: "POST",
      });

      // Refetch results immediately
      setResultsLoading(true);
      try {
        const [resultsData, evidenceData] = await Promise.all([
          apiRequest<JobResultsResponse>(`/jobs/${id}/results`),
          apiRequest<JobEvidenceResponse>(`/jobs/${id}/evidence`).catch(() => null),
        ]);
        setCandidateCount(resultsData.candidate_count);
        setResults(resultsData.rows || []);
        if (evidenceData && evidenceData.rows) {
          const map: Record<string, EvidenceItem[]> = {};
          for (const row of evidenceData.rows) {
            map[row.candidate_id] = row.evidence || [];
          }
          setEvidenceMap(map);
        }
      } finally {
        setResultsLoading(false);
      }

      setSuccessMsg(`Deterministic scores recalculated for ${res.candidates_scored} candidate(s).`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setRunError(err.message || "Failed to recalculate scores.");
    } finally {
      setScoreLoading(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !job) return;

    const trimmedTitle = editTitle.trim();
    const trimmedDesc = editDescription.trim();

    if (trimmedTitle.length < 1 || trimmedTitle.length > 200) {
      setError("Title must be between 1 and 200 characters.");
      return;
    }
    if (trimmedDesc.length < 30 || trimmedDesc.length > 20000) {
      setError("Description must be between 30 and 20,000 characters.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await apiRequest<Job>(`/jobs/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: trimmedTitle,
          description: trimmedDesc,
        }),
      });

      setJob(updated);
      setIsEditing(false);
      setSuccessMsg("Job updated successfully.");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to save job changes.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setDeleting(true);
    try {
      await apiRequest(`/jobs/${id}`, {
        method: "DELETE",
      });
      navigate("/jobs");
    } catch (err: any) {
      alert(err.message || "Failed to delete job.");
      setDeleting(false);
    }
  };

  const getStatusBadge = (status: Job["status"]) => {
    switch (status) {
      case "draft":
        return <Badge variant="outline" className="bg-slate-50 text-slate-700 border-slate-200">Draft</Badge>;
      case "processing":
        return (
          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 flex items-center gap-1">
            <RotateCw className="h-3 w-3 animate-spin" />
            <span>Processing</span>
          </Badge>
        );
      case "done":
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Done</Badge>;
      case "failed":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getLabelBadge = (label?: string | null) => {
    switch (label) {
      case "strong_match":
        return (
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
            <span>Strong Match</span>
          </Badge>
        );
      case "needs_review":
        return (
          <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 font-semibold flex items-center gap-1">
            <AlertCircle className="h-3 w-3 text-amber-600" />
            <span>Needs Review</span>
          </Badge>
        );
      case "insufficient_evidence":
        return (
          <Badge variant="outline" className="bg-slate-100 text-slate-700 border-slate-300 font-medium flex items-center gap-1">
            <HelpCircle className="h-3 w-3 text-slate-500" />
            <span>Insufficient Evidence</span>
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="bg-slate-50 text-slate-500 border-slate-200">
            Unscored
          </Badge>
        );
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <div className="h-40 rounded-xl border border-slate-200 bg-slate-50/50 animate-pulse" />
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Link to="/jobs">
              <Button variant="outline" size="sm" className="ml-4">
                Back to Jobs
              </Button>
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!job) return null;

  const isProcessing = job.status === "processing";
  const hasCandidates = candidateCount > 0;
  const hasRankings = results.length > 0;
  const canRunRetrieval = hasCandidates && !isProcessing && !runLoading;
  const canVerify = hasRankings && !isProcessing && !verifyLoading;
  const canScore = hasRankings && !isProcessing && !scoreLoading;

  // Counts of recommendations
  const strongCount = results.filter((r) => r.label === "strong_match").length;
  const reviewCount = results.filter((r) => r.label === "needs_review").length;
  const insufficientCount = results.filter((r) => r.label === "insufficient_evidence").length;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 space-y-8">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/jobs"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Jobs</span>
        </Link>

        <div className="flex items-center gap-2">
          {job.status === "draft" && !isEditing && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-1.5 text-xs"
            >
              <Edit3 className="h-3.5 w-3.5" />
              <span>Edit Job</span>
            </Button>
          )}

          {confirmDelete ? (
            <div className="flex items-center gap-1 bg-red-50 p-1 rounded-md border border-red-200">
              <Button
                variant="destructive"
                size="sm"
                className="text-xs h-7 px-2"
                disabled={deleting}
                onClick={handleDelete}
              >
                {deleting ? "Deleting..." : "Confirm Delete"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-7 px-2"
                disabled={deleting}
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConfirmDelete(true)}
              className="text-slate-400 hover:text-red-600 text-xs flex items-center gap-1"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Delete</span>
            </Button>
          )}
        </div>
      </div>

      {/* Global Alerts */}
      {successMsg && (
        <Alert variant="success">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{successMsg}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Job Info Card */}
      <Card className="shadow-sm border-slate-200">
        <CardHeader className="border-b border-slate-100 pb-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <CardTitle className="text-xl font-bold text-slate-900">{job.title}</CardTitle>
                {getStatusBadge(job.status)}
              </div>
              <CardDescription className="flex items-center gap-4 text-xs pt-1">
                <span className="flex items-center gap-1 text-slate-500">
                  <Calendar className="h-3.5 w-3.5" />
                  Created {new Date(job.created_at).toLocaleDateString()}
                </span>
                <span className="text-slate-500">
                  Updated {new Date(job.updated_at).toLocaleDateString()}
                </span>
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6">
          {job.status === "failed" && job.error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Processing error:</strong> {job.error}
              </AlertDescription>
            </Alert>
          )}

          {isEditing ? (
            <form onSubmit={handleSaveEdit} className="space-y-5" noValidate>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="edit-title">Job Title</Label>
                  <span className="text-xs text-slate-400">{editTitle.trim().length} / 200</span>
                </div>
                <Input
                  id="edit-title"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  disabled={saving}
                  required
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="edit-description">Job Description</Label>
                  <span className="text-xs text-slate-400">
                    {editDescription.trim().length} / 20,000 (min 30 characters)
                  </span>
                </div>
                <Textarea
                  id="edit-description"
                  rows={8}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  disabled={saving}
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={saving}
                  onClick={() => {
                    setIsEditing(false);
                    setEditTitle(job.title);
                    setEditDescription(job.description);
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          ) : (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Job Description
              </h4>
              <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-4 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {job.description}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Candidates & Ingestion Card */}
      <Card className="shadow-sm border-slate-200">
        <CardHeader className="border-b border-slate-100 pb-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-indigo-600" />
                <CardTitle className="text-lg font-bold text-slate-900">Candidate Pool</CardTitle>
                <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200">
                  {candidateCount} {candidateCount === 1 ? "candidate" : "candidates"}
                </Badge>
              </div>
              <CardDescription className="text-xs pt-1">
                Upload resumes in CSV format to populate the candidate pool for this position.
              </CardDescription>
            </div>

            <div className="flex items-center gap-3">
              <a
                href="/sample-candidates.csv"
                download="sample-candidates.csv"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download sample CSV</span>
              </a>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6 space-y-6">
          {/* Replace confirmation dialog/alert */}
          {showReplaceConfirm && (
            <div className="rounded-lg border border-amber-300 bg-amber-50/80 p-4 space-y-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h5 className="text-sm font-semibold text-amber-900">Replace Existing Candidates?</h5>
                  <p className="text-xs text-amber-800 mt-1">
                    This job already contains {candidateCount} candidate{candidateCount === 1 ? "" : "s"}.
                    Uploading a new file will replace all previous candidates and clear existing retrieval rankings.
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowReplaceConfirm(false);
                    setPendingFile(null);
                  }}
                  disabled={uploading}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={uploading || !pendingFile}
                  onClick={() => {
                    if (pendingFile) executeUpload(pendingFile, true);
                  }}
                >
                  {uploading ? "Replacing..." : "Replace Candidates"}
                </Button>
              </div>
            </div>
          )}

          {/* Drag & Drop File Upload Area */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              const file = e.dataTransfer.files?.[0];
              if (file) handleFileSelect(file);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all ${
              isDragOver
                ? "border-indigo-500 bg-indigo-50/50"
                : "border-slate-200 hover:border-slate-300 bg-slate-50/30"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
              }}
              accept=".csv"
              className="hidden"
            />
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 mb-3">
              <UploadCloud className="h-6 w-6" />
            </div>
            <p className="text-sm font-medium text-slate-800">
              {uploading ? "Uploading & validating CSV..." : "Click to select or drag and drop candidate CSV"}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports CSV format • Maximum 5 MB • Up to 1,000 candidate rows
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Required column: <code>name</code> • Resume columns: <code>resume_text</code>, <code>summary</code>, <code>skills</code>, <code>experience</code>
            </p>
          </div>

          {uploadError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{uploadError}</AlertDescription>
            </Alert>
          )}

          {/* Validation Rejections Table */}
          {uploadReport && uploadReport.rows_rejected && uploadReport.rows_rejected.length > 0 && (
            <div className="space-y-2 rounded-lg border border-red-200 bg-red-50/30 p-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <h5 className="text-xs font-semibold uppercase tracking-wider text-red-900">
                  Validation Report: {uploadReport.rows_rejected.length} row{uploadReport.rows_rejected.length === 1 ? "" : "s"} rejected
                </h5>
              </div>
              <div className="max-h-48 overflow-y-auto rounded-md border border-red-200 bg-white">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="border-b border-red-100 bg-red-50/50 text-[11px] font-semibold text-red-800">
                    <tr>
                      <th className="px-3 py-2 w-24">Row #</th>
                      <th className="px-3 py-2">Rejection Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {uploadReport.rows_rejected.map((r, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-3 py-1.5 font-mono text-slate-500">{r.row_number}</td>
                        <td className="px-3 py-1.5 text-red-700">{r.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Retrieval Trigger Action Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-100">
            <div>
              <h4 className="text-sm font-semibold text-slate-900">Hybrid Retrieval Matching</h4>
              <p className="text-xs text-slate-500">
                Matches candidate resumes against the job description using dense vector search and keyword matching.
              </p>
            </div>

            <Button
              onClick={handleRunRetrieval}
              disabled={!canRunRetrieval}
              className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 shadow-sm"
            >
              {isProcessing || runLoading ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin" />
                  <span>Retrieval in progress...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Run Retrieval</span>
                </>
              )}
            </Button>
          </div>

          {!hasCandidates && !isProcessing && (
            <p className="text-xs text-slate-400 text-right">
              Upload at least one candidate resume to enable retrieval.
            </p>
          )}

          {runMessage && (
            <Alert variant="default" className="border-indigo-200 bg-indigo-50/50 text-indigo-900">
              <RotateCw className="h-4 w-4 animate-spin text-indigo-600" />
              <AlertDescription>{runMessage}</AlertDescription>
            </Alert>
          )}

          {runError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{runError}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Ranked Results Card with Evidence & Deterministic Scoring */}
      <Card className="shadow-sm border-slate-200">
        <CardHeader className="border-b border-slate-100 pb-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Search className="h-5 w-5 text-indigo-600" />
                <CardTitle className="text-lg font-bold text-slate-900">Ranked Results & Evidence</CardTitle>
                {results.length > 0 && (
                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                    {results.length} ranked
                  </Badge>
                )}
              </div>
              <CardDescription className="text-xs pt-1">
                Multi-signal ranking combining dense semantic retrieval, public proof of work, and deterministic confidence weighting.
              </CardDescription>

              {/* Recommendation summary pills */}
              {results.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  <span className="text-[11px] font-medium text-slate-500">Breakdown:</span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {strongCount} Strong Match
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    {reviewCount} Needs Review
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {insufficientCount} Insufficient Evidence
                  </span>
                </div>
              )}
            </div>

            {/* Action Buttons for Evidence & Scoring */}
            {hasRankings && (
              <div className="flex flex-wrap items-center gap-2">
                {/* Verify Evidence Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleVerifyEvidence}
                  disabled={!canVerify}
                  className="bg-indigo-50/50 hover:bg-indigo-100/70 border-indigo-200 text-indigo-700 flex items-center gap-1.5 text-xs shadow-xs"
                  title="Collects GitHub and LeetCode evidence for top candidates in background, then scores results"
                >
                  {verifyLoading || (isProcessing && !runLoading) ? (
                    <>
                      <RotateCw className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                      <span>Verifying Evidence...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" />
                      <span>Verify Evidence</span>
                    </>
                  )}
                </Button>

                {/* Recalculate Scores Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRecalculateScores}
                  disabled={!canScore}
                  className="border-slate-200 text-slate-700 hover:bg-slate-100 flex items-center gap-1.5 text-xs shadow-xs"
                  title="Recomputes deterministic scoring from cached evidence without external API calls"
                >
                  {scoreLoading ? (
                    <>
                      <RotateCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Scoring...</span>
                    </>
                  ) : (
                    <>
                      <Sliders className="h-3.5 w-3.5 text-slate-500" />
                      <span>Recalculate Scores</span>
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="pt-6">
          {resultsLoading ? (
            <div className="space-y-3 py-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-16 rounded-lg bg-slate-100/60 animate-pulse" />
              ))}
            </div>
          ) : resultsError ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{resultsError}</AlertDescription>
            </Alert>
          ) : results.length === 0 ? (
            <div className="py-12 text-center">
              <FileText className="mx-auto h-10 w-10 text-slate-300 mb-2" />
              <h4 className="text-sm font-medium text-slate-700">No ranked candidates yet</h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                {hasCandidates
                  ? "Click 'Run Retrieval' above to match and rank candidates against this job description."
                  : "Upload a CSV candidate roster to get started."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-700">
                <thead className="border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase tracking-wider bg-slate-50/50">
                  <tr>
                    <th className="px-4 py-3 w-16 text-center">Rank</th>
                    <th className="px-4 py-3 min-w-[220px]">Candidate & Profiles</th>
                    <th className="px-4 py-3 w-40">Recommendation</th>
                    <th className="px-4 py-3 min-w-[170px]">Score Breakdown</th>
                    <th className="px-4 py-3 min-w-[140px]">Proof Confidence</th>
                    <th className="px-4 py-3 w-28 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {results.map((row) => {
                    const finalScoreDisplay = row.final_score !== null && row.final_score !== undefined
                      ? row.final_score
                      : row.retrieval_score;
                    const finalScorePercent = (finalScoreDisplay * 100).toFixed(1);
                    const retrievalPercent = (row.retrieval_score * 100).toFixed(0);
                    const confidencePercent = ((row.confidence ?? 0) * 100).toFixed(0);
                    const candidateEvidence = evidenceMap[row.candidate_id] || [];

                    return (
                      <tr
                        key={row.candidate_id}
                        onClick={() => setSelectedCandidate(row)}
                        className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                      >
                        {/* Rank */}
                        <td className="px-4 py-4 text-center">
                          <span
                            className={`inline-flex items-center justify-center h-7 w-7 rounded-full text-xs font-bold font-mono ${
                              row.rank === 1
                                ? "bg-amber-100 text-amber-900 border border-amber-300"
                                : row.rank === 2
                                ? "bg-slate-200 text-slate-800 border border-slate-300"
                                : row.rank === 3
                                ? "bg-amber-50 text-amber-800 border border-amber-200"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            #{row.rank}
                          </span>
                        </td>

                        {/* Candidate Name & Evidence Chips */}
                        <td className="px-4 py-4 space-y-1.5">
                          <div className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors flex items-center gap-1.5">
                            <span>{row.name}</span>
                          </div>
                          <EvidenceChips evidence={candidateEvidence} />
                        </td>

                        {/* Recommendation Label Badge */}
                        <td className="px-4 py-4">
                          {getLabelBadge(row.label)}
                        </td>

                        {/* Final Score & Breakdown */}
                        <td className="px-4 py-4">
                          <div className="space-y-1">
                            <div className="flex items-baseline justify-between">
                              <span className="text-base font-extrabold text-slate-900 font-mono">
                                {finalScorePercent}%
                              </span>
                              <span className="text-[11px] text-slate-500">
                                {row.final_score !== null && row.final_score !== undefined ? "Final" : "Retrieval"}
                              </span>
                            </div>

                            <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                                style={{ width: `${Math.min(100, Math.max(0, Number(finalScorePercent)))}%` }}
                              />
                            </div>

                            <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                              <span>R: {retrievalPercent}%</span>
                              <span>
                                {row.evidence_score !== null && row.evidence_score !== undefined
                                  ? `E: ${(row.evidence_score * 100).toFixed(0)}%`
                                  : "E: None"}
                              </span>
                            </div>
                          </div>
                        </td>

                        {/* Proof Confidence Level */}
                        <td className="px-4 py-4">
                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-xs font-semibold">
                              <span className={
                                (row.confidence ?? 0) >= 0.5
                                  ? "text-emerald-700"
                                  : (row.confidence ?? 0) > 0.2
                                  ? "text-amber-700"
                                  : "text-slate-500"
                              }>
                                {confidencePercent}%
                              </span>
                              <span className="text-[10px] font-normal text-slate-400">
                                {(row.confidence ?? 0) >= 0.5
                                  ? "High"
                                  : (row.confidence ?? 0) > 0.2
                                  ? "Medium"
                                  : "Low"}
                              </span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-300 ${
                                  (row.confidence ?? 0) >= 0.5
                                    ? "bg-emerald-500"
                                    : (row.confidence ?? 0) > 0.2
                                    ? "bg-amber-500"
                                    : "bg-slate-300"
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, Number(confidencePercent)))}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedCandidate(row);
                            }}
                            className="text-xs text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 font-medium flex items-center gap-1 ml-auto"
                          >
                            <span>Breakdown</span>
                            <ChevronRight className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Slide-out Score Breakdown & Proof Reasons Drawer */}
      {selectedCandidate && (
        <ScoreBreakdownDrawer
          candidate={selectedCandidate}
          evidence={evidenceMap[selectedCandidate.candidate_id] || []}
          jobTitle={job.title}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  );
};
