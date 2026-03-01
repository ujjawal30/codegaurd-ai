import { useCallback, useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { uploadZip, triggerAnalysis, subscribeProgress, listAnalyses, type ProgressEvent } from "@/lib/api";
import type { AnalysisJobSummary, Phase } from "@/lib/types";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Upload, Code, ShieldCheck, BarChart3, AlertCircle, CheckCircle2, Loader2, FileArchive, ArrowRight } from "lucide-react";
import FeatureCard from "@/components/cards/FeatureCard";
import { STAGE_LABELS } from "@/constants";

export default function UploadPage() {
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase
  >("idle");
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [, setJobId] = useState("");

  const [recentAudits, setRecentAudits] = useState<AnalysisJobSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    listAnalyses(1)
      .then((res) => setRecentAudits(res.items.slice(0, 5)))
      .catch(console.error)
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".zip")) {
        setError("Only .zip files are supported.");
        return;
      }
      setPhase("uploading");
      setFileName(file.name);
      setError("");

      try {
        const upload = await uploadZip(file);
        setJobId(upload.job_id);
        setPhase("processing");
        setProgress(5);
        setStage("extract");
        await triggerAnalysis(upload.job_id);

        subscribeProgress(
          upload.job_id,
          (ev: ProgressEvent) => {
            setProgress(ev.progress);
            setStage(ev.stage);
          },
          (_ev: ProgressEvent) => {
            setPhase("done");
            setProgress(100);
            setStage("completed");
            setTimeout(() => navigate(`/analysis/${upload.job_id}`), 1200);
          },
          (ev: ProgressEvent | string) => {
            setPhase("error");
            setError(typeof ev === "string" ? ev : (ev.error ?? "Analysis failed"));
          },
        );
      } catch (err: any) {
        setPhase("error");
        setError(err?.response?.data?.detail ?? err?.message ?? "Upload failed");
      }
    },
    [navigate],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (phase !== "idle") return;
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile, phase],
  );

  return (
    <div className="animate-fade-in space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {phase === "idle" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInput.current?.click()}
              className={`
                rounded-xl border-2 border-dashed cursor-pointer h-84
                flex flex-col items-center justify-center text-center transition-all
                ${
                  dragOver
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-border hover:border-emerald-500/40 bg-linear-to-b from-emerald-500/3 to-transparent"
                }
              `}
            >
              <div className="flex flex-col items-center gap-4 px-6 max-w-md">
                <div className="w-14 h-14 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <Upload className="w-6 h-6 text-emerald-500" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-foreground mb-1">Upload Repository</h2>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Drag and drop a Python project (.zip) or click to browse. The pipeline will analyze architecture, security, and code quality.
                  </p>
                </div>
                <Button size="sm" className="mt-1 bg-emerald-600 hover:bg-emerald-700 text-white">
                  <FileArchive className="w-4 h-4 mr-1.5" />
                  Select .zip file
                </Button>
              </div>
              <input
                ref={fileInput}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </div>
          )}

          {phase !== "idle" && (
            <Card className="h-84 flex flex-col items-center justify-center animate-fade-in">
              <CardContent className="flex flex-col items-center justify-center w-full max-w-sm p-6">
                {phase === "error" ? (
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                      <AlertCircle className="w-6 h-6 text-red-500" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">Analysis Failed</h3>
                    <p className="text-sm text-muted-foreground mb-6">{error}</p>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setPhase("idle");
                        setError("");
                      }}
                    >
                      Try Again
                    </Button>
                  </div>
                ) : phase === "done" ? (
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    </div>
                    <h3 className="text-lg font-semibold mb-1">Analysis Complete</h3>
                    <p className="text-sm text-muted-foreground">Redirecting to results…</p>
                  </div>
                ) : (
                  <div className="w-full">
                    <div className="flex items-center gap-2 mb-1">
                      <Loader2 className="w-4 h-4 text-emerald-500 animate-spin" />
                      <span className="text-sm font-medium truncate">{fileName}</span>
                    </div>
                    <div className="flex items-center justify-between mb-2 mt-3">
                      <span className="text-xs text-muted-foreground">{phase === "uploading" ? "Uploading…" : STAGE_LABELS[stage] || stage}</span>
                      <span className="text-xs font-mono text-emerald-500 font-medium">{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-1.5 [&>div]:bg-emerald-500" />
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <Card className="gap-4">
          <CardHeader className="">
            <CardTitle className="text-sm font-medium text-muted-foreground">Recent Audits</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 pt-0">
            {loadingHistory ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            ) : recentAudits.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">No audits yet</p>
            ) : (
              <>
                {recentAudits.map((job) => (
                  <Link
                    key={job.job_id}
                    to={job.status === "completed" ? `/analysis/${job.job_id}` : "#"}
                    className={`flex items-center justify-between py-2.5 px-2 rounded-md transition-colors -mx-2 ${
                      job.status === "completed" ? "hover:bg-muted" : "opacity-50 pointer-events-none"
                    }`}
                  >
                    <div className="min-w-0 mr-3">
                      <p className="text-sm font-medium truncate">{job.filename}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{job.created_at ? new Date(job.created_at).toLocaleDateString() : ""}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {job.status === "completed" ? (
                        <Badge className="text-[10px] px-1.5 bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/20 border-0">{job.status}</Badge>
                      ) : job.status === "failed" ? (
                        <Badge variant="destructive" className="text-[10px] px-1.5">
                          {job.status}
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[10px] px-1.5">
                          {job.status}
                        </Badge>
                      )}
                      {job.status === "completed" && <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />}
                    </div>
                  </Link>
                ))}
                <Link
                  to="/history"
                  className="block text-xs text-emerald-500 hover:text-emerald-400 transition-colors text-center pt-3 pb-1 font-medium"
                >
                  View all →
                </Link>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard
          icon={<Code className="w-5 h-5" />}
          title="Static Analysis"
          desc="AST parsing, Radon metrics, Ruff linting, and Bandit security scanning."
          color="text-blue-400"
          bg="bg-blue-500/10"
        />
        <FeatureCard
          icon={<ShieldCheck className="w-5 h-5" />}
          title="AI-Powered Review"
          desc="LLM-driven issue detection grounded in RAG-retrieved best practices."
          color="text-emerald-400"
          bg="bg-emerald-500/10"
        />
        <FeatureCard
          icon={<BarChart3 className="w-5 h-5" />}
          title="Actionable Output"
          desc="Prioritized roadmap, generated tests, and validation scoring."
          color="text-amber-400"
          bg="bg-amber-500/10"
        />
      </div>
    </div>
  );
}
