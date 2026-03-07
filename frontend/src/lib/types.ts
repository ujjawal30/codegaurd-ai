/**
 * CodeGuard AI — Frontend TypeScript types
 *
 * Mirrors backend Pydantic schemas for type safety.
 */

/* ── Enums ────────────────────────────────────────────────────── */

export type Severity = "low" | "medium" | "high" | "critical";
export type FileRole = "controller" | "model" | "service" | "utility" | "config" | "test" | "migration" | "script" | "other";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type EffortEstimate = "trivial" | "small" | "medium" | "large" | "major";
export type IssueCategory = "performance" | "security" | "maintainability" | "style" | "architecture" | "error_handling" | "testing" | "logic_bug";

export type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export type SortDirection = "none" | "desc" | "asc";

/* ── Tool Results ─────────────────────────────────────────────── */

export interface FunctionInfo {
  name: string;
  lineno: number;
  end_lineno: number | null;
  args: string[];
  decorators: string[];
  docstring: string | null;
  is_async: boolean;
  complexity: number;
}

export interface ClassInfo {
  name: string;
  lineno: number;
  end_lineno: number | null;
  bases: string[];
  methods: FunctionInfo[];
  docstring: string | null;
}

export interface ImportInfo {
  module: string;
  names: string[];
  is_from_import: boolean;
  lineno: number;
}

export interface ASTAnalysis {
  file_path: string;
  functions: FunctionInfo[];
  classes: ClassInfo[];
  imports: ImportInfo[];
  total_lines: number;
  has_main_guard: boolean;
}

export interface RadonMetrics {
  file_path: string;
  cyclomatic_complexity: number;
  maintainability_index: number;
  loc: number;
  sloc: number;
  comments: number;
  blank_lines: number;
  complexity_rank: string;
}

export interface RuffIssue {
  code: string;
  message: string;
  line: number;
  column: number;
  severity: Severity;
}

export interface BanditIssue {
  test_id: string;
  issue_text: string;
  severity: Severity;
  confidence: Severity;
  line_range: number[];
}

export interface ToolResults {
  ast_results: Record<string, ASTAnalysis>;
  radon_results: Record<string, RadonMetrics>;
  ruff_results: Record<string, RuffIssue[]>;
  bandit_results: Record<string, BanditIssue[]>;
}

/* ── LLM Pipeline Results ─────────────────────────────────────── */

export interface FileClassification {
  file_path: string;
  role: FileRole;
  confidence: number;
  reasoning: string;
}

export interface RAGContext {
  title: string;
  category: string;
  content: string;
  relevance_score: number;
}

export interface DetectedIssue {
  file_path: string;
  line_range: number[];
  category: IssueCategory;
  severity: Severity;
  title: string;
  description: string;
  suggestion: string;
  grounding: string;
}

export interface RefactorTask {
  priority: number;
  title: string;
  affected_files: string[];
  effort_estimate: EffortEstimate;
  description: string;
  rationale: string;
  related_issues: string[];
}

export interface RefactorRoadmap {
  tasks: RefactorTask[];
  summary: string;
  estimated_total_effort: string;
}

export interface GeneratedTest {
  target_function: string;
  target_file: string;
  test_code: string;
  rationale: string;
  risk_level: RiskLevel;
}

export interface ValidationResult {
  is_valid: boolean;
  confidence_score: number;
  issues_found: string[];
  suggestions: string[];
  summary: string;
}

/* ── Full Analysis Response ───────────────────────────────────── */

export interface AnalysisResponse {
  job_id: string;
  filename: string;
  status: string;
  file_count: number;
  tool_results: ToolResults;
  file_classifications: FileClassification[];
  rag_context: RAGContext[];
  detected_issues: DetectedIssue[];
  refactor_roadmap: RefactorRoadmap | null;
  generated_tests: GeneratedTest[];
  validation_result: ValidationResult | null;
  summary: string;
}

/* ── Job Summary (for list view) ──────────────────────────────── */

export interface AnalysisJobSummary {
  job_id: string;
  filename: string;
  status: string;
  current_stage: string | null;
  file_count: number | null;
  created_at: string | null;
  updated_at: string | null;
  error_message: string | null;
}
