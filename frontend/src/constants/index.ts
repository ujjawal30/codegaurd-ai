import type { EffortEstimate, IssueCategory, Severity } from "@/lib/types";

export const STAGE_LABELS: Record<string, string> = {
  pending: "Initializing pipeline…",
  extract: "Extracting files…",
  static_analysis: "Running static analysis…",
  classify: "Classifying file roles…",
  rag_retrieve: "Retrieving best practices…",
  detect_issues: "Detecting issues…",
  generate_roadmap: "Generating roadmap…",
  generate_tests: "Generating tests…",
  validate: "Validating results…",
  completed: "Analysis complete",
};

export const CATEGORIES: IssueCategory[] = [
  "performance",
  "security",
  "maintainability",
  "style",
  "architecture",
  "error_handling",
  "testing",
  "logic_bug",
];

export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export const EFFORTS: EffortEstimate[] = ["trivial", "small", "medium", "large", "major"];
