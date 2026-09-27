/** Product requirements used to evaluate benchmark reports in the UI. */
export const PRD_TARGETS = {
  quality_scorer: {
    metric: "jev_accuracy",
    min: 0.85,
    label: "Action agreement ≥ 85%",
  },
  bundle_router: {
    metric: "jev_accuracy",
    min: 0.9,
    label: "Routing accuracy ≥ 90%",
  },
  notifiable_detector: {
    recallMin: 0.95,
    precisionMin: 0.8,
    label: "Recall ≥ 95%, precision ≥ 80%",
  },
  latency: { p50MaxMs: 30, p95MaxMs: 100 },
} as const;
