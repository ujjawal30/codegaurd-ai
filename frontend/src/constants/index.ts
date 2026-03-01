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
