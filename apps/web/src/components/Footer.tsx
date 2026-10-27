import React, { useEffect, useState, useCallback } from "react";
import { CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export const Footer: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);

  const apiUrl = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const response = await fetch(`${apiUrl.replace(/\/+$/, "")}/health`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      const end = performance.now();
      setLatency(Math.round(end - start));

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: HealthResponse = await response.json();
      setHealthData(data);
    } catch (err: unknown) {
      const end = performance.now();
      setLatency(Math.round(end - start));
      setError(err instanceof Error ? err.message : "Unreachable");
      setHealthData(null);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const isHealthy = !loading && !error && healthData?.status === "healthy";

  return (
    <footer className="mt-auto border-t border-slate-200 bg-slate-50 py-6 text-xs text-slate-500">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
        <div>
          <span className="font-semibold text-slate-700">VeriHire v2</span> &middot; Evidence-backed candidate intelligence
        </div>

        {/* Small /health Status Card */}
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-1.5 shadow-xs">
          <span className="font-medium text-slate-600">API Health:</span>
          {loading ? (
            <Badge variant="outline" className="text-slate-500">Checking...</Badge>
          ) : isHealthy ? (
            <div className="flex items-center gap-1.5 text-emerald-600 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Healthy {latency !== null ? `(${latency}ms)` : ""}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-red-600 font-medium">
              <XCircle className="h-3.5 w-3.5" />
              <span>Unreachable</span>
            </div>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={checkHealth}
            disabled={loading}
            className="h-6 w-6 p-0 text-slate-400 hover:text-slate-700"
            aria-label="Refresh API health status"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>
    </footer>
  );
};
