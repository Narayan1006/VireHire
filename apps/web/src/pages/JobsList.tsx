import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, Briefcase, Calendar, Trash2, AlertCircle, RefreshCw } from "lucide-react";

export interface Job {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  status: "draft" | "processing" | "done" | "failed";
  error: string | null;
  created_at: string;
  updated_at: string;
}

export const JobsListPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<Job[]>("/jobs?limit=50&offset=0");
      setJobs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleDelete = async (jobId: string) => {
    setDeletingId(jobId);
    try {
      await apiRequest(`/jobs/${jobId}`, {
        method: "DELETE",
      });
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      setConfirmDeleteId(null);
    } catch (err: any) {
      alert(err.message || "Failed to delete job");
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusBadge = (status: Job["status"]) => {
    switch (status) {
      case "draft":
        return <Badge variant="outline" className="bg-slate-50 text-slate-700 border-slate-200">Draft</Badge>;
      case "processing":
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Processing</Badge>;
      case "done":
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Done</Badge>;
      case "failed":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage your open roles and candidate evaluation pipelines
          </p>
        </div>
        <Link to="/jobs/new">
          <Button className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            <span>New Job</span>
          </Button>
        </Link>
      </div>

      {/* Error state */}
      {error && (
        <Alert variant="destructive" className="mt-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchJobs} className="ml-4 h-7 text-xs">
              <RefreshCw className="mr-1 h-3 w-3" /> Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {loading && (
        <div className="mt-8 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-slate-200 bg-slate-50/50 animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && jobs.length === 0 && (
        <div className="mt-12 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 p-12 text-center bg-slate-50/50">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 mb-4">
            <Briefcase className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900">No jobs created yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mt-1 mb-6">
            Get started by posting a job description to evaluate candidates with verifiable evidence.
          </p>
          <Link to="/jobs/new">
            <Button className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              <span>Create your first job</span>
            </Button>
          </Link>
        </div>
      )}

      {/* Jobs list */}
      {!loading && !error && jobs.length > 0 && (
        <div className="mt-6 space-y-3">
          {jobs.map((job) => (
            <Card key={job.id} className="transition-all hover:border-slate-300 hover:shadow-xs">
              <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/jobs/${job.id}`}
                      className="text-base font-semibold text-slate-900 hover:text-indigo-600 truncate transition-colors"
                    >
                      {job.title}
                    </Link>
                    {getStatusBadge(job.status)}
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-1">
                    {job.description}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {new Date(job.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center">
                  <Link to={`/jobs/${job.id}`}>
                    <Button variant="outline" size="sm" className="text-xs">
                      View details
                    </Button>
                  </Link>

                  {confirmDeleteId === job.id ? (
                    <div className="flex items-center gap-1 bg-red-50 p-1 rounded-md border border-red-200">
                      <Button
                        variant="destructive"
                        size="sm"
                        className="text-xs h-7 px-2"
                        disabled={deletingId === job.id}
                        onClick={() => handleDelete(job.id)}
                      >
                        {deletingId === job.id ? "Deleting..." : "Confirm"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-7 px-2"
                        disabled={deletingId === job.id}
                        onClick={() => setConfirmDeleteId(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-400 hover:text-red-600 h-8 w-8 p-0"
                      aria-label={`Delete job ${job.title}`}
                      onClick={() => setConfirmDeleteId(job.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
