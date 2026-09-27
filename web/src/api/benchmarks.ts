/** Hand-written report types: benchmark report bodies are intentionally untyped in OpenAPI. */
export type BenchmarkModuleName =
  "quality_scorer" | "bundle_router" | "notifiable_detector";
export interface AccuracyBreakdown {
  count: number;
  jev_accuracy: number;
  rule_accuracy: number;
}
export interface BenchmarkRow {
  fixture: string;
  jev_correct: boolean;
  rule_correct: boolean;
  expected_action?: string;
  jev_action?: string;
  rule_action?: string;
  expected_category?: string;
  jev_category?: string;
  rule_category?: string;
  expected_notifiable?: boolean;
  jev_notifiable?: boolean;
  rule_notifiable?: boolean;
}
export interface Prf {
  precision: number;
  recall: number;
  f1: number;
}
export interface BenchmarkModule {
  fixture_count: number;
  jev_accuracy: number;
  rule_accuracy: number;
  latency: { mean_ms: number; p50_ms: number; p95_ms: number };
  confidence_calibration: Array<{
    bucket: string;
    count: number;
    mean_confidence: number;
    observed_accuracy: number;
  }>;
  rows: BenchmarkRow[];
  breakdown?: {
    source: Record<string, AccuracyBreakdown>;
    difficulty: Record<string, AccuracyBreakdown>;
  };
  unapproved_labels?: number;
  jev_precision_recall_f1?: Prf;
  rule_precision_recall_f1?: Prf;
}
export interface BenchmarkReport {
  generated_at: string;
  mode: "mock_jev" | "live_jev";
  jev_model?: string | null;
  dataset?: "unit" | "full";
  quality_labels_banded?: boolean;
  token_and_cost?: {
    tokens_used: number;
    estimated_cost_usd: number;
    pricing_note?: string;
  };
  modules: Record<BenchmarkModuleName, BenchmarkModule>;
}
