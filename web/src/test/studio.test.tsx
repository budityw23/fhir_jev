import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { CompareResponse, DemoConfig, FixtureEntry } from "../api/types";
import { DecisionCard } from "../components/studio/DecisionCard";
import { FixturePicker } from "../components/studio/FixturePicker";
import { ProbabilityBars } from "../components/studio/ProbabilityBars";
import { QuestionBox } from "../components/studio/QuestionBox";
import { ScoreGauge } from "../components/studio/ScoreGauge";
import { ThresholdSliders } from "../components/studio/ThresholdSliders";
import { VerdictStrip } from "../components/studio/VerdictStrip";
import { questionsFor, Studio } from "../pages/Studio";
import notifiable from "./fixtures/compare_notifiable.json";
import quality from "./fixtures/compare_quality.json";
import router from "./fixtures/compare_router.json";

const hooks = vi.hoisted(() => ({
  compare: vi.fn(),
  health: { data: { jev_client: "mock" } },
}));

vi.mock("../api/queries", () => ({
  useCompare: hooks.compare,
  useDemoConfig: () => ({ data: demoConfig }),
  useFixture: () => ({ data: qualityResource }),
  useFixtures: () => ({ data: fixtures }),
  useHealth: () => hooks.health,
}));

const demoConfig: DemoConfig = {
  mode: "mock",
  jev_model: null,
  route_options: [],
  thresholds: quality.thresholds,
  questions: {
    QUALITY_SCORE_QUESTION: "quality question",
    NIK_VALIDATION_STATEMENT: "NIK statement",
    ROUTE_QUESTION: "route question",
    NOTIFIABLE_STATEMENT: "notifiable statement",
  },
};
const qualityResource = { resourceType: "Patient", id: "fixture" };
const fixtures: FixtureEntry[] = [
  {
    id: "one", name: "alpha", label: "Alpha", source: "unit", resource_type: "Patient",
    module: "quality", difficulty: "easy", approved: true, ground_truth: {},
  },
  {
    id: "two", name: "needle", label: "Needle", source: "hard", resource_type: "Patient",
    module: "quality", difficulty: "hard", approved: false, ground_truth: {},
  },
  {
    id: "generated/patient", name: "generated_003", label: "Auto accept", source: "generated",
    resource_type: "Patient", module: "quality", difficulty: "easy", approved: true,
    ground_truth: {},
  },
  {
    id: "generated/observation", name: "generated_003", label: "Review", source: "generated",
    resource_type: "Observation", module: "quality", difficulty: "easy", approved: true,
    ground_truth: {},
  },
];

describe("Studio decision components", () => {
  it("VerdictStrip hides without ground truth.", () => {
    const { container } = render(
      <VerdictStrip
        verdict={{ jev_correct: null, rule_correct: null }}
        jevDecision="x"
        ruleDecision="x"
        groundTruth={null}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("VerdictStrip shows quality and router ground-truth expectations.", () => {
    const { rerender } = render(
      <VerdictStrip
        verdict={quality.verdict}
        jevDecision={quality.jev_decision}
        ruleDecision={quality.rule.decision}
        groundTruth={quality.ground_truth}
      />,
    );
    expect(screen.getByText("Ground truth: auto_accept")).toBeVisible();
    rerender(
      <VerdictStrip
        verdict={router.verdict}
        jevDecision={router.jev_decision}
        ruleDecision={router.rule.decision}
        groundTruth={router.ground_truth}
      />,
    );
    expect(screen.getByText("Ground truth: unknown")).toBeVisible();
  });

  it("ProbabilityBars shows the override note.", () => {
    render(
      <ProbabilityBars
        probabilities={{ unknown: 0.1, lab_result: 0.92 }}
        winner="lab_result"
        floor={0.99}
        overridden
      />,
    );
    expect(screen.getByText("overridden: confidence 0.92 < 0.99")).toBeVisible();
  });

  it("DecisionCard renders samples with lane icons and exact reasons.", () => {
    const samples = [quality, router, notifiable] as CompareResponse[];
    for (const sample of samples) {
      const { unmount } = render(<DecisionCard data={sample} />);
      expect(screen.getByTestId("lane")).toHaveTextContent(laneText(sample.lane));
      expect(screen.getByTestId("lane-reason")).toHaveTextContent(sample.lane_reason);
      unmount();
    }
  });

  it("shows score distributions only for live Jev.", () => {
    hooks.health.data.jev_client = "mock";
    const { rerender } = render(<DecisionCard data={quality as CompareResponse} />);
    expect(screen.queryByText("Score distribution")).not.toBeInTheDocument();
    hooks.health.data.jev_client = "live";
    rerender(<DecisionCard data={quality as CompareResponse} />);
    expect(screen.getByText("Score distribution")).toBeVisible();
    hooks.health.data.jev_client = "mock";
  });

  it("shows Dinkes only for flagged decisions.", () => {
    const unflagged = { ...notifiable, lane: "review" } as CompareResponse;
    const { rerender } = render(<DecisionCard data={unflagged} />);
    expect(screen.queryByText(/Report to Dinkes/)).not.toBeInTheDocument();
    rerender(<DecisionCard data={notifiable as CompareResponse} />);
    expect(screen.getByText(/Report to Dinkes/)).toBeVisible();
  });

  it("shows only the selected module threshold sliders.", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <ThresholdSliders module="quality" value={quality.thresholds} onChange={onChange} />,
    );
    expect(screen.getByLabelText("Quality threshold")).toBeVisible();
    expect(screen.queryByLabelText("Route confidence minimum")).not.toBeInTheDocument();
    rerender(<ThresholdSliders module="router" value={quality.thresholds} onChange={onChange} />);
    expect(screen.getByLabelText("Route confidence minimum")).toBeVisible();
    expect(screen.queryByLabelText("Quality threshold")).not.toBeInTheDocument();
  });

  it("draws score and threshold positions as distinct radial SVG attributes", () => {
    const view = render(<ScoreGauge confidence={0.71} score={80} threshold={70} />);
    const scoreArc = (): SVGPathElement => (
      view.container.querySelector("[data-testid='score-arc']")!
    );
    const thresholdTick = (): SVGLineElement => (
      view.container.querySelector("[data-testid='threshold-tick']")!
    );
    const arcAt80 = scoreArc().getAttribute("stroke-dasharray");
    expect(tickCoordinate(thresholdTick(), "x1")).toBeCloseTo(147.02, 1);
    expect(tickCoordinate(thresholdTick(), "y1")).toBeCloseTo(35.28, 1);
    expect(tickCoordinate(thresholdTick(), "x1")).toBeGreaterThan(100);
    expect(tickCoordinate(thresholdTick(), "y1")).toBeLessThan(100);
    const { rerender } = view;
    rerender(<ScoreGauge confidence={0.71} score={20} threshold={85} />);
    expect(scoreArc()).toHaveAttribute("stroke-dasharray", "20 100");
    expect(scoreArc()).not.toHaveAttribute("stroke-dasharray", arcAt80 ?? "");
    expect(tickCoordinate(thresholdTick(), "x1")).not.toBeCloseTo(147.02, 1);
    rerender(<ScoreGauge confidence={0.71} score={20} threshold={50} />);
    expect(tickCoordinate(thresholdTick(), "x1")).toBeCloseTo(100, 1);
    expect(tickCoordinate(thresholdTick(), "y1")).toBeCloseTo(20, 1);
    rerender(<ScoreGauge confidence={0.71} score={20} threshold={0} />);
    expect(tickCoordinate(thresholdTick(), "x1")).toBeCloseTo(20, 1);
    expect(tickCoordinate(thresholdTick(), "y1")).toBeCloseTo(100, 1);
  });

  it("groups, searches, and marks draft fixtures.", async () => {
    const user = userEvent.setup();
    render(<FixturePicker module="quality" value={null} onChange={vi.fn()} />);
    expect(screen.getByRole("group", { name: "unit" })).toBeVisible();
    expect(screen.getByRole("group", { name: "hard" })).toBeVisible();
    expect(screen.getByText("alpha")).toBeVisible();
    expect(screen.getByText("Alpha")).toBeVisible();
    expect(screen.getByText("generated_003 · Patient")).toBeVisible();
    expect(screen.getByText("generated_003 · Observation")).toBeVisible();
    expect(screen.getByText("draft")).toBeVisible();
    await user.type(screen.getByLabelText("Search fixtures"), "needle");
    expect(screen.getByLabelText("needle")).toBeVisible();
    expect(screen.queryByLabelText("alpha")).not.toBeInTheDocument();
  });

  it("shows the exact router question constant.", () => {
    render(<QuestionBox questions={questionsFor("router", demoConfig.questions)} />);
    expect(screen.getByText("route question")).toBeVisible();
  });

  it("debounces rapid Studio slider changes into one compare.", async () => {
    vi.useFakeTimers();
    hooks.compare.mockReturnValue({ data: quality, error: null });
    renderStudio();
    await vi.advanceTimersByTimeAsync(250);
    hooks.compare.mockClear();
    const slider = screen.getByLabelText("Quality threshold");
    fireEvent.change(slider, { target: { value: "71" } });
    fireEvent.change(slider, { target: { value: "72" } });
    fireEvent.change(slider, { target: { value: "73" } });
    await vi.advanceTimersByTimeAsync(249);
    expect(compareCallsFor(73)).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(1);
    expect(compareCallsFor(73)).toHaveLength(1);
    vi.useRealTimers();
  });
});

function laneText(lane: CompareResponse["lane"]): string {
  return {
    auto_accepted: "✓ auto_accepted",
    routed: "✓ routed",
    flagged: "⚑ flagged",
    review: "⚠ review",
  }[lane];
}

function tickCoordinate(element: SVGLineElement, name: "x1" | "y1"): number {
  return Number(element.getAttribute(name));
}

function renderStudio(): void {
  render(
    <MemoryRouter initialEntries={["/studio/quality?fixture=one"]}>
      <Routes><Route path="/studio/:module" element={<Studio />} /></Routes>
    </MemoryRouter>,
  );
}

function compareCallsFor(threshold: number): unknown[][] {
  return hooks.compare.mock.calls.filter(([, input]) => {
    const request = input as { thresholds?: { quality_threshold?: number } } | null;
    return request?.thresholds?.quality_threshold === threshold;
  });
}
