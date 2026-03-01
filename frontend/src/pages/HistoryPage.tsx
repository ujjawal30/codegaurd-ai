import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAnalyses } from "@/lib/api";
import type { AnalysisJobSummary } from "@/lib/types";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle2, XCircle, Clock, ArrowRight, Upload } from "lucide-react";

export default function HistoryPage() {
  const [jobs, setJobs] = useState<AnalysisJobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    setLoading(true);
    listAnalyses(page)
      .then((res) => {
        setJobs(res.items);
        setTotalPages(res.total_pages);
      })
      .finally(() => setLoading(false));
  }, [page]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Audit History</h1>
        <p className="text-sm text-muted-foreground mt-1">Previous analysis runs and their results.</p>
      </div>

      {jobs.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center flex flex-col items-center">
            <p className="text-sm text-muted-foreground mb-4">No audits found.</p>
            <Button asChild className="bg-emerald-600 hover:bg-emerald-700 text-white">
              <Link to="/">
                <Upload className="w-4 h-4 mr-1.5" />
                Upload Repository
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="gap-2 py-4">
          <CardHeader className="pb-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">{jobs.length} results</CardTitle>
          </CardHeader>
          <CardContent>
            {jobs.map((job, idx) => {
              const StatusIcon = job.status === "completed" ? CheckCircle2 : job.status === "failed" ? XCircle : Clock;
              const iconColor = job.status === "completed" ? "text-emerald-500" : job.status === "failed" ? "text-red-400" : "text-muted-foreground";

              return (
                <Link
                  key={job.job_id}
                  to={job.status === "completed" ? `/analysis/${job.job_id}` : "#"}
                  className={`relative flex items-center gap-4 py-4 transition-colors group ${
                    job.status === "completed" ? "hover:bg-muted/50 -mx-4 px-4 rounded-md" : "opacity-60 pointer-events-none"
                  }`}
                >
                  {idx !== 0 && <div className="absolute border-t border-muted top-0 left-4 right-4" />}
                  <StatusIcon className={`w-5 h-5 shrink-0 ${iconColor}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate group-hover:text-foreground">{job.filename}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {job.created_at ? new Date(job.created_at).toLocaleString() : ""}
                      {job.file_count ? ` · ${job.file_count} files` : ""}
                    </p>
                    {job.error_message && <p className="text-xs text-red-400 mt-1 truncate">{job.error_message}</p>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {job.status === "completed" ? (
                      <Badge className="text-[10px] bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/20 border-0">{job.status}</Badge>
                    ) : job.status === "failed" ? (
                      <Badge variant="destructive" className="text-[10px]">
                        {job.status}
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-[10px]">
                        {job.status}
                      </Badge>
                    )}
                    {job.status === "completed" && (
                      <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-emerald-500 transition-colors" />
                    )}
                  </div>
                </Link>
              );
            })}
          </CardContent>
        </Card>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-6">
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            Previous
          </Button>
          <span className="text-xs text-muted-foreground px-3">
            {page} / {totalPages}
          </span>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
