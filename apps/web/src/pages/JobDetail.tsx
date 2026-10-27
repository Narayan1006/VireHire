import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ArrowLeft, Calendar, Edit3, Trash2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Job } from "@/pages/JobsList";

export const JobDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

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

  const fetchJob = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<Job>(`/jobs/${id}`);
      setJob(data);
      setEditTitle(data.title);
      setEditDescription(data.description);
    } catch (err: any) {
      setError(err.message || "Failed to load job details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
  }, [id]);

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
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Processing</Badge>;
      case "done":
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">Done</Badge>;
      case "failed":
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <div className="h-40 rounded-xl border border-slate-200 bg-slate-50/50 animate-pulse" />
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
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

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center justify-between">
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

      {successMsg && (
        <Alert variant="success" className="mb-6">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{successMsg}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="shadow-sm">
        <CardHeader className="border-b border-slate-100 pb-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <CardTitle className="text-xl font-bold text-slate-900">{job.title}</CardTitle>
                {getStatusBadge(job.status)}
              </div>
              <CardDescription className="flex items-center gap-4 text-xs pt-1">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  Created {new Date(job.created_at).toLocaleDateString()}
                </span>
                <span>
                  Updated {new Date(job.updated_at).toLocaleDateString()}
                </span>
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6">
          {job.error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>Error during processing: {job.error}</AlertDescription>
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
                  rows={12}
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
            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Job Description
                </h4>
                <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-4 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {job.description}
                </div>
              </div>

              {job.status !== "draft" && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
                  This job is currently in <strong className="font-semibold">{job.status}</strong> status and cannot be edited.
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
