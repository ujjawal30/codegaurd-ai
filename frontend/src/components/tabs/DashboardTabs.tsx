import { useState, useMemo } from "react";
import type { AnalysisResponse, DetectedIssue, GeneratedTest, SortDirection } from "@/lib/types";
import { renderMarkdown } from "@/lib/utils";
import { CATEGORIES, SEVERITIES, EFFORTS } from "@/constants";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { FiltersBar, MultiFilterPopover, SortButton } from "@/components/shared/FiltersBar";
import { ChevronRight, TestTube2 } from "lucide-react";
import Empty from "@/components/shared/Empty";

const SEV_STYLES: Record<string, { badge: string; bar: string }> = {
  critical: { badge: "bg-red-500/15 text-red-400 border-0 hover:bg-red-500/20", bar: "[&>div]:bg-red-500" },
  high: { badge: "bg-orange-500/15 text-orange-400 border-0 hover:bg-orange-500/20", bar: "[&>div]:bg-orange-500" },
  medium: { badge: "bg-yellow-500/15 text-yellow-400 border-0 hover:bg-yellow-500/20", bar: "[&>div]:bg-yellow-400" },
  low: { badge: "bg-emerald-500/15 text-emerald-400 border-0 hover:bg-emerald-500/20", bar: "[&>div]:bg-emerald-500" },
};

export function OverviewTab({ data, severityCounts }: { data: AnalysisResponse; severityCounts: Record<string, number> }) {
  const total = data.detected_issues.length || 1;
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Severity Distribution</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(["critical", "high", "medium", "low"] as const).map((s) => {
            const count = severityCounts[s] ?? 0;
            const style = SEV_STYLES[s];
            return (
              <div key={s} className="flex items-center gap-3">
                <Badge className={`w-16 justify-center text-[10px] ${style.badge}`}>{s}</Badge>
                <Progress value={(count / total) * 100} className={`flex-1 h-1.5 ${style.bar}`} />
                <span className="text-xs font-mono text-muted-foreground w-6 text-right">{count}</span>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">File Roles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {data.file_classifications?.map((clf) => (
            <div key={clf.file_path} className="flex items-center justify-between py-1.5 text-sm">
              <code className="text-xs text-muted-foreground truncate pr-4 font-mono">{clf.file_path}</code>
              <Badge variant="outline" className="text-[10px] shrink-0">
                {clf.role}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {data.validation_result && (
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm">Validation Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground leading-relaxed">{data.validation_result.summary}</p>
            {data.validation_result.suggestions.length > 0 && (
              <ul className="mt-4 space-y-2">
                {data.validation_result.suggestions.map((s, i) => (
                  <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                    <ChevronRight className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export function IssuesTab({ issues }: { issues: DetectedIssue[] }) {
  const [categoryFilter, setCategoryFilter] = useState<Set<string>>(new Set());
  const [severityFilter, setSeverityFilter] = useState<Set<string>>(new Set());
  const [sortDirection, setSortDirection] = useState<SortDirection>("none");

  const filteredIssues = useMemo(() => {
    let result = issues;

    if (categoryFilter.size > 0) {
      result = result.filter((i) => categoryFilter.has(i.category));
    }
    if (severityFilter.size > 0) {
      result = result.filter((i) => severityFilter.has(i.severity));
    }
    if (sortDirection !== "none") {
      result = [...result].sort((a, b) => {
        const diff = SEVERITIES.indexOf(a.severity) - SEVERITIES.indexOf(b.severity);
        return sortDirection === "desc" ? diff : -diff;
      });
    }

    return result;
  }, [issues, categoryFilter, severityFilter, sortDirection]);

  const isFiltered = categoryFilter.size > 0 || severityFilter.size > 0 || sortDirection !== "none";

  const clearAll = () => {
    setCategoryFilter(new Set());
    setSeverityFilter(new Set());
    setSortDirection("none");
  };

  const cycleSortDirection = () => {
    setSortDirection((prev) => (prev === "none" ? "desc" : prev === "desc" ? "asc" : "none"));
  };

  if (!issues.length) return <Empty label="No issues detected." />;

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <FiltersBar isFiltered={isFiltered} clearAll={clearAll} filteredCount={filteredIssues.length} totalCount={issues.length}>
        <MultiFilterPopover label="Category" options={CATEGORIES} selected={categoryFilter} onChange={setCategoryFilter} />
        <MultiFilterPopover label="Severity" options={SEVERITIES} selected={severityFilter} onChange={setSeverityFilter} />
        <SortButton
          direction={sortDirection}
          onClick={cycleSortDirection}
          labels={{ idle: "Sort Severity", asc: "Critical First", desc: "Low First" }}
        />
      </FiltersBar>

      {/* Issue Cards */}
      {filteredIssues.length === 0 ? (
        <Empty label="No issues match the current filters." />
      ) : (
        <div className="space-y-3">
          {filteredIssues.map((issue, i) => (
            <Card key={i}>
              <CardContent className="px-5">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="font-medium text-sm">{issue.title}</h4>
                  <div className="flex gap-1.5 shrink-0">
                    <Badge variant="outline" className="text-[10px]">
                      {issue.category}
                    </Badge>
                    <Badge className={`text-[10px] ${SEV_STYLES[issue.severity]?.badge ?? ""}`}>{issue.severity}</Badge>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{issue.description}</p>
                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <code className="font-mono">{issue.file_path}</code>
                  {issue.line_range?.length > 0 && <span>L{issue.line_range.join("–")}</span>}
                </div>
                {issue.suggestion && (
                  <div className="mt-3 p-3 rounded-md bg-emerald-500/5 border border-emerald-500/10 text-sm">
                    <span className="font-medium text-xs text-emerald-500">Suggestion: </span>
                    <span className="text-foreground">{issue.suggestion}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export function RoadmapTab({ roadmap }: { roadmap: AnalysisResponse["refactor_roadmap"] }) {
  const [fileFilter, setFileFilter] = useState<Set<string>>(new Set());
  const [effortFilter, setEffortFilter] = useState<Set<string>>(new Set());
  const [sortDirection, setSortDirection] = useState<SortDirection>("none");

  const allFiles = useMemo(() => {
    if (!roadmap?.tasks.length) return [];
    const set = new Set<string>();
    roadmap.tasks.forEach((t) => t.affected_files.forEach((f) => set.add(f)));
    return [...set].sort();
  }, [roadmap]);

  const filteredTasks = useMemo(() => {
    if (!roadmap?.tasks.length) return [];
    let result = [...roadmap.tasks];

    if (fileFilter.size > 0) {
      result = result.filter((t) => t.affected_files.some((f) => fileFilter.has(f)));
    }
    if (effortFilter.size > 0) {
      result = result.filter((t) => effortFilter.has(t.effort_estimate));
    }

    if (sortDirection !== "none") {
      result.sort((a, b) => {
        const diff = EFFORTS.indexOf(a.effort_estimate) - EFFORTS.indexOf(b.effort_estimate);
        return sortDirection === "desc" ? -diff : diff;
      });
    } else {
      result.sort((a, b) => a.priority - b.priority);
    }

    return result;
  }, [roadmap, fileFilter, effortFilter, sortDirection]);

  const isFiltered = fileFilter.size > 0 || effortFilter.size > 0 || sortDirection !== "none";

  const clearAll = () => {
    setFileFilter(new Set());
    setEffortFilter(new Set());
    setSortDirection("none");
  };

  const cycleSortDirection = () => {
    setSortDirection((prev) => (prev === "none" ? "asc" : prev === "asc" ? "desc" : "none"));
  };

  if (!roadmap?.tasks.length) return <Empty label="No refactoring tasks." />;

  return (
    <div className="space-y-4">
      <Card className="bg-blue-500/5 border-blue-500/10">
        <CardContent className="px-5">
          <p className="text-sm leading-relaxed">{roadmap.summary}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Estimated effort: <strong className="text-blue-400">{roadmap.estimated_total_effort}</strong>
          </p>
        </CardContent>
      </Card>

      <FiltersBar isFiltered={isFiltered} clearAll={clearAll} filteredCount={filteredTasks.length} totalCount={roadmap.tasks.length}>
        <MultiFilterPopover label="Files" options={allFiles} selected={fileFilter} onChange={setFileFilter} />
        <MultiFilterPopover label="Effort" options={EFFORTS} selected={effortFilter} onChange={setEffortFilter} />
        <SortButton
          direction={sortDirection}
          onClick={cycleSortDirection}
          labels={{ idle: "Sort Effort", asc: "Easiest First", desc: "Hardest First" }}
          accent="blue"
        />
      </FiltersBar>

      {filteredTasks.length === 0 ? (
        <Empty label="No tasks match the current filters." />
      ) : (
        filteredTasks.map((task, i) => (
          <Card key={i}>
            <CardContent className="px-5">
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded bg-blue-500/15 flex items-center justify-center text-xs font-semibold text-blue-400">
                    {task.priority}
                  </span>
                  <h4 className="font-medium text-sm">{task.title}</h4>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  {task.effort_estimate}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed ml-8">{task.description}</p>
              {task.affected_files.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 ml-8">
                  {task.affected_files.map((f) => (
                    <code key={f} className="text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                      {f}
                    </code>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

export function TestsTab({ tests }: { tests: GeneratedTest[] }) {
  if (!tests.length) return <Empty label="No tests generated." />;
  return (
    <Accordion type="single" collapsible className="w-full space-y-3">
      {tests.map((test, i) => (
        <AccordionItem key={i} value={`item-${i}`} className="border-0">
          <Card className="overflow-hidden">
            {/* Accordion trigger = header */}
            <AccordionTrigger className="hover:no-underline p-0 [&>svg]:mr-4 [&>svg]:text-muted-foreground">
              <div className="flex items-center gap-3 px-5 w-full">
                <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0">
                  <TestTube2 className="w-4 h-4 text-violet-400" />
                </div>
                <div className="min-w-0 text-left flex-1">
                  <p className="font-medium text-sm truncate">{test.target_function}</p>
                  <p className="text-xs text-muted-foreground font-mono mt-0.5">{test.target_file}</p>
                </div>
                <Badge className={`text-[10px] shrink-0 ${SEV_STYLES[test.risk_level]?.badge ?? "bg-secondary text-secondary-foreground"}`}>
                  {test.risk_level}
                </Badge>
              </div>
            </AccordionTrigger>

            <AccordionContent className="p-0">
              {/* Rationale */}
              <div className="px-5 py-3 bg-muted/30 border-t border-border">
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Rationale</p>
                <div
                  className="text-sm text-foreground/80 leading-relaxed [&_br]:mb-1"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(test.rationale) }}
                />
              </div>

              {/* Code */}
              <div className="border-t border-border">
                <div className="flex items-center justify-between px-4 py-1.5 bg-muted/50 border-b border-border">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Python</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(test.test_code.replace(/```python\n?|```/g, ""))}
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors uppercase tracking-wider font-medium"
                  >
                    Copy
                  </button>
                </div>
                <pre className="m-0! rounded-none! border-0! text-xs overflow-x-auto p-4 bg-[hsl(0_0%_7%)]">
                  <code className="text-emerald-300/90">{test.test_code.replace(/```python\n?|```/g, "")}</code>
                </pre>
              </div>
            </AccordionContent>
          </Card>
        </AccordionItem>
      ))}
    </Accordion>
  );
}

export function FilesTab({ data }: { data: AnalysisResponse }) {
  const radon = data.tool_results?.radon_results ?? {};
  const ruff = data.tool_results?.ruff_results ?? {};
  const bandit = data.tool_results?.bandit_results ?? {};
  const ast = data.tool_results?.ast_results ?? {};
  const files = Object.keys({ ...radon, ...ast }).sort();
  const roleMap = Object.fromEntries((data.file_classifications ?? []).map((c) => [c.file_path, c.role]));
  if (!files.length) return <Empty label="No file metrics." />;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {files.map((fp) => {
          const r = radon[fp];
          const a = ast[fp];
          const ruffCount = ruff[fp]?.length ?? 0;
          const banditCount = bandit[fp]?.length ?? 0;
          const role = roleMap[fp];
          return (
            <Card key={fp}>
              <CardContent className="px-5">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <h4 className="font-mono text-xs font-medium truncate" title={fp}>
                    {fp}
                  </h4>
                  {role && (
                    <Badge variant="outline" className="text-[10px] shrink-0">
                      {role}
                    </Badge>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  {r ? (
                    <>
                      <div>
                        <span className="text-muted-foreground block mb-0.5" title="Cyclomatic Complexity — lower is simpler">
                          CC
                        </span>
                        <span className="font-mono font-medium">
                          {r.cyclomatic_complexity} <span className="text-blue-400">({r.complexity_rank})</span>
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block mb-0.5" title="Maintainability Index — 0 to 100, higher is better">
                          MI
                        </span>
                        <span className="font-mono font-medium">{r.maintainability_index}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block mb-0.5" title="Source Lines of Code">
                          SLOC
                        </span>
                        <span className="font-mono font-medium">{r.sloc}</span>
                      </div>
                    </>
                  ) : (
                    <div className="col-span-3 text-muted-foreground italic">No metrics</div>
                  )}
                </div>
                <div className="flex gap-4 mt-3 text-xs">
                  <span className={ruffCount > 0 ? "text-yellow-500" : "text-muted-foreground"} title="Ruff style and quality warnings">
                    {ruffCount} lint
                  </span>
                  <span className={banditCount > 0 ? "text-red-400" : "text-muted-foreground"} title="Bandit security findings">
                    {banditCount} security
                  </span>
                </div>
                {a && (a.functions.length > 0 || a.classes.length > 0) && (
                  <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t">
                    {a.classes.map((cls) => (
                      <code key={cls.name} className="text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono">
                        class {cls.name}
                      </code>
                    ))}
                    {a.functions.map((fn) => (
                      <code key={fn.name} className="text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                        {fn.is_async ? "async " : ""}
                        {fn.name}()
                      </code>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Metrics legend */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-px rounded-lg border border-muted overflow-hidden text-[11px]">
        <div className="bg-muted/20 px-4 py-3 space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-2">Metrics</p>
          <p className="text-muted-foreground">
            <strong className="text-foreground/70 font-medium">CC</strong> - Cyclomatic Complexity{" "}
            <span className="text-muted-foreground/50">(lower = simpler)</span>
          </p>
          <p className="text-muted-foreground">
            <strong className="text-foreground/70 font-medium">MI</strong> - Maintainability Index{" "}
            <span className="text-muted-foreground/50">(0–100, higher = better)</span>
          </p>
          <p className="text-muted-foreground">
            <strong className="text-foreground/70 font-medium">SLOC</strong> - Source Lines of Code
          </p>
          <p className="text-muted-foreground">
            <strong className="text-yellow-500/80 font-medium">lint</strong> - Ruff style & quality warnings
          </p>
          <p className="text-muted-foreground">
            <strong className="text-red-400/80 font-medium">security</strong> - Bandit security findings
          </p>
        </div>
        <div className="bg-muted/20 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-2">Complexity Rank</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-muted-foreground">
            <p>
              <strong className="text-emerald-400 font-mono">A</strong> - Simple
            </p>
            <p>
              <strong className="text-emerald-400 font-mono">B</strong> - Well-structured
            </p>
            <p>
              <strong className="text-yellow-400 font-mono">C</strong> - Slightly complex
            </p>
            <p>
              <strong className="text-yellow-400 font-mono">D</strong> - Moderately complex
            </p>
            <p>
              <strong className="text-orange-400 font-mono">E</strong> - Complex
            </p>
            <p>
              <strong className="text-red-400 font-mono">F</strong> - Very complex
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
