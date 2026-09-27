import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import liveFixture from "./fixtures/benchmark-live.synthetic.json";
import type { BenchmarkReport } from "../api/benchmarks";
import {
  AccuracyTable,
  BreakdownTable,
  DisagreementList,
  LatencyPanel,
  LiveMeta,
  LiveVsMock,
  MockDisclaimer,
  UnapprovedBanner,
} from "../components/benchmarks/BenchmarkParts";

function report(overrides: Partial<BenchmarkReport> = {}): BenchmarkReport {
  const module = (accuracy: number) => ({
    fixture_count: 2,
    jev_accuracy: accuracy,
    rule_accuracy: 0.8,
    latency: { mean_ms: 10, p50_ms: 30, p95_ms: 100 },
    confidence_calibration: [],
    breakdown: { source: {}, difficulty: {} },
    unapproved_labels: 0,
    rows: [
      {
        fixture: "tests/fixtures/bundles/lab_bundle.json",
        jev_correct: false,
        rule_correct: false,
        expected_action: "x",
        jev_action: "y",
        rule_action: "z",
      },
      {
        fixture: "same",
        jev_correct: true,
        rule_correct: true,
        expected_action: "x",
        jev_action: "x",
        rule_action: "x",
      },
    ],
  });
  return {
    generated_at: "2026-09-27T12:00:00Z",
    mode: "mock_jev",
    dataset: "full",
    quality_labels_banded: true,
    modules: {
      quality_scorer: module(0.85),
      bundle_router: module(0.733),
      notifiable_detector: {
        ...module(0.9),
        jev_precision_recall_f1: { precision: 0.8, recall: 0.95, f1: 0.87 },
        rule_precision_recall_f1: { precision: 0.9, recall: 0.9, f1: 0.9 },
      },
    },
    ...overrides,
  };
}
describe("benchmark components", () => {
  it("LabelGuard hides quality accuracy for unbanded reports.", () => {
    const { rerender } = render(
      <AccuracyTable report={report({ quality_labels_banded: false })} />,
    );
    expect(
      screen.getAllByText("labels not suitable for live scoring"),
    ).not.toHaveLength(0);
    rerender(
      <AccuracyTable report={report({ quality_labels_banded: undefined })} />,
    );
    expect(
      screen.getAllByText("labels not suitable for live scoring"),
    ).not.toHaveLength(0);
  });
  it("The PRD chip shows FAIL for 0.733 routing.", () => {
    render(<AccuracyTable report={report()} />);
    expect(
      screen.getAllByText("FAIL · Routing accuracy ≥ 90%"),
    ).not.toHaveLength(0);
    expect(
      screen.getAllByText("PASS · Action agreement ≥ 85%"),
    ).not.toHaveLength(0);
  });
  it("shows full-only, mode-only, labels, disagreements, and latency evidence.", () => {
    const base = report();
    const { rerender } = render(
      <MemoryRouter>
        <BreakdownTable report={base} />
        <MockDisclaimer report={base} />
        <UnapprovedBanner report={base} />
        <LatencyPanel report={base} />
        <DisagreementList report={base} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Breakdown")).toBeVisible();
    expect(
      screen.getByText(
        "Mock decisions mirror rule logic; this report validates the harness, not Jev.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Quality:.*lab_bundle/ }),
    ).toHaveAttribute(
      "href",
      "/studio/quality?fixture=tests%2Ffixtures%2Fbundles%2Flab_bundle.json",
    );
    expect(
      screen.getByRole("link", { name: /Router:.*lab_bundle/ }),
    ).toHaveAttribute(
      "href",
      "/studio/router?fixture=tests%2Ffixtures%2Fbundles%2Flab_bundle.json",
    );
    expect(
      screen.getByRole("link", { name: /Notifiable:.*lab_bundle/ }),
    ).toHaveAttribute(
      "href",
      "/studio/notifiable?fixture=tests%2Ffixtures%2Fbundles%2Flab_bundle.json",
    );
    expect(screen.queryByText(/^Unapproved labels:/)).not.toBeInTheDocument();
    rerender(
      <BreakdownTable report={report({ dataset: "unit", mode: "live_jev" })} />,
    );
    expect(screen.queryByText("Breakdown")).not.toBeInTheDocument();
  });
  it("shows live metadata and comparison only when both modes exist.", () => {
    const live = liveFixture as BenchmarkReport;
    const { rerender } = render(
      <>
        <LiveMeta report={live} />
        <LiveVsMock reports={[live, report()]} selected={live} />
      </>,
    );
    expect(screen.getByText(/synthetic-live-model/)).toBeVisible();
    expect(screen.getByText(/Total tokens: 1234/)).toBeVisible();
    expect(screen.getByText(/Estimated cost: \$0.000052/)).toBeVisible();
    expect(screen.getByText("Live vs mock")).toBeVisible();
    rerender(<LiveVsMock reports={[live]} selected={live} />);
    expect(screen.queryByText("Live vs mock")).not.toBeInTheDocument();
  });
});
