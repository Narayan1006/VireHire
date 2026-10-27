import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { Job } from "@/pages/JobsList";

export const JobNewPage: React.FC = () => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const titleLength = title.trim().length;
  const descLength = description.trim().length;

  const validate = (): boolean => {
    if (titleLength < 1 || titleLength > 200) {
      setError("Job title must be between 1 and 200 characters.");
      return false;
    }
    if (descLength < 30 || descLength > 20000) {
      setError("Job description must be between 30 and 20,000 characters.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validate()) return;

    setLoading(true);
    try {
      const created = await apiRequest<Job>("/jobs", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
        }),
      });

      navigate(`/jobs/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create job.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <Link
          to="/jobs"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Jobs</span>
        </Link>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-xl font-bold text-slate-900">Create New Job</CardTitle>
          <CardDescription>
            Define the role and description to start processing and scoring candidates
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit} noValidate>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Title */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="job-title">Job Title</Label>
                <span className={`text-xs ${titleLength > 200 ? "text-red-500 font-semibold" : "text-slate-400"}`}>
                  {titleLength} / 200
                </span>
              </div>
              <Input
                id="job-title"
                placeholder="e.g. Senior Machine Learning Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="job-description">Job Description</Label>
                <span
                  className={`text-xs ${
                    descLength > 20000 || (descLength > 0 && descLength < 30)
                      ? "text-amber-600 font-semibold"
                      : "text-slate-400"
                  }`}
                >
                  {descLength} / 20,000 (min 30 characters)
                </span>
              </div>
              <Textarea
                id="job-description"
                placeholder="Paste the full job requirements, skills, responsibilities, and qualifications..."
                rows={10}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          </CardContent>

          <CardFooter className="flex items-center justify-end gap-3 border-t border-slate-100 bg-slate-50/50 p-6">
            <Link to="/jobs">
              <Button type="button" variant="outline" disabled={loading}>
                Cancel
              </Button>
            </Link>
            <Button
              type="submit"
              disabled={loading || titleLength < 1 || titleLength > 200 || descLength < 30 || descLength > 20000}
            >
              {loading ? "Creating..." : "Create Job"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};
