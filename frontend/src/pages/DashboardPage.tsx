import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getAnalysis } from "@/lib/api";
import type { AnalysisResponse } from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  FileText,
  AlertTriangle,
  ClipboardList,
  TestTube2,
  FolderOpen,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Bug,
  ListChecks,
  TrendingUp,
} from "lucide-react";
import { FilesTab, IssuesTab, OverviewTab, RoadmapTab, TestsTab } from "@/components/tabs/DashboardTabs";
import StatCard from "@/components/cards/StatCard";

export default function DashboardPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    getAnalysis(jobId)
      .then((d) => setData(d as AnalysisResponse))
      .catch((e) => setError(e?.response?.data?.detail ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-sm text-muted-foreground">{error || "No data available"}</p>
        <Link to="/" className="text-sm text-emerald-500 hover:underline">
          ← Back to upload
        </Link>
      </div>
    );
  }

  const issues = data.detected_issues ?? [];
  const roadmap = data.refactor_roadmap;
  const tests = data.generated_tests ?? [];
  const validation = data.validation_result;

  const severityCounts = issues.reduce(
    (acc, i) => {
      acc[i.severity] = (acc[i.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );
  const radonEntries = Object.values(data.tool_results?.radon_results ?? {});
  const avgMI = radonEntries.length ? (radonEntries.reduce((s, r) => s + r.maintainability_index, 0) / radonEntries.length).toFixed(1) : "—";

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div>
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4">
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-2xl font-semibold tracking-tight">{data.filename}</h1>
          {validation && (
            <Badge className={validation.is_valid ? "bg-emerald-500/15 text-emerald-400 border-0" : "bg-yellow-500/15 text-yellow-400 border-0"}>
              {validation.is_valid ? (
                <>
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Validated
                </>
              ) : (
                "Needs Review"
              )}
              {" · "}
              {Math.round(validation.confidence_score * 100)}%
            </Badge>
          )}
        </div>
        {data.summary && <p className="text-sm text-muted-foreground mt-2 max-w-3xl leading-relaxed">{data.summary}</p>}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Files Analyzed" value={data.file_count} icon={<FileCode className="w-4 h-4" />} color="text-blue-400" bg="bg-blue-500/10" />
        <StatCard label="Issues Found" value={issues.length} icon={<Bug className="w-4 h-4" />} color="text-red-400" bg="bg-red-500/10" />
        <StatCard
          label="Refactor Tasks"
          value={roadmap?.tasks.length ?? 0}
          icon={<ListChecks className="w-4 h-4" />}
          color="text-amber-400"
          bg="bg-amber-500/10"
        />
        <StatCard label="Avg MI Score" value={avgMI} icon={<TrendingUp className="w-4 h-4" />} color="text-emerald-400" bg="bg-emerald-500/10" />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList variant="line" className="border-b border-border w-full justify-start gap-0">
          <TabsTrigger value="overview" className="px-4 py-2.5 data-[state=active]:text-emerald-500 data-[state=active]:after:bg-emerald-500">
            <FileText className="w-4 h-4 mr-1.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="issues" className="px-4 py-2.5 data-[state=active]:text-emerald-500 data-[state=active]:after:bg-emerald-500">
            <AlertTriangle className="w-4 h-4 mr-1.5" />
            Issues ({issues.length})
          </TabsTrigger>
          <TabsTrigger value="roadmap" className="px-4 py-2.5 data-[state=active]:text-emerald-500 data-[state=active]:after:bg-emerald-500">
            <ClipboardList className="w-4 h-4 mr-1.5" />
            Roadmap
          </TabsTrigger>
          <TabsTrigger value="tests" className="px-4 py-2.5 data-[state=active]:text-emerald-500 data-[state=active]:after:bg-emerald-500">
            <TestTube2 className="w-4 h-4 mr-1.5" />
            Tests ({tests.length})
          </TabsTrigger>
          <TabsTrigger value="files" className="px-4 py-2.5 data-[state=active]:text-emerald-500 data-[state=active]:after:bg-emerald-500">
            <FolderOpen className="w-4 h-4 mr-1.5" />
            Files
          </TabsTrigger>
        </TabsList>

        <div className="mt-6">
          <TabsContent value="overview">
            <OverviewTab data={data} severityCounts={severityCounts} />
          </TabsContent>
          <TabsContent value="issues">
            <IssuesTab issues={issues} />
          </TabsContent>
          <TabsContent value="roadmap">
            <RoadmapTab roadmap={roadmap} />
          </TabsContent>
          <TabsContent value="tests">
            <TestsTab tests={tests} />
          </TabsContent>
          <TabsContent value="files">
            <FilesTab data={data} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
