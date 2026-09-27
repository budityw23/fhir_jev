import type { components } from "./schema";

/** Backend schema aliases generated from OpenAPI; do not duplicate server models here. */
export type CompareResponse = components["schemas"]["CompareResponse"];
export type FixtureEntry = components["schemas"]["FixtureEntry"];
export type DemoConfig = components["schemas"]["DemoConfig"];
export type Thresholds = components["schemas"]["Thresholds"];
export type DecisionEvent = components["schemas"]["DecisionEvent"];
export type BenchmarkSummary = components["schemas"]["BenchmarkSummary"];
export type CompareRequest = components["schemas"]["CompareRequest"];
export type ThresholdOverrides = components["schemas"]["ThresholdOverrides"];
export type DemoModule = CompareResponse["module"];

// These two responses are not exported by the backend OpenAPI schema.
export interface ErrorBody {
  error: string;
  detail: string | null;
  request_id: string;
  timestamp: string;
}
// Run events exist only on the SSE stream, so they are intentionally handwritten.
export interface RunEvent {
  run_id: string;
  status: "started" | "finished" | "stopped";
  total: number;
  processed: number;
}
export interface Health {
  status: string;
  jev_client: "mock" | "live";
  jev_model: string | null;
  version: string;
}
