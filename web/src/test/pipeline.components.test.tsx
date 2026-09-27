import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { DecisionEvent } from "../api/types";
import {
  LiveFeed,
  RerunDelta,
  ReviewQueue,
  StatsStrip,
} from "../components/pipeline/PipelineParts";
import { RunControls } from "../components/pipeline/RunControls";
import {
  initialPipelineState,
  type PipelineState,
  type RunSummary,
} from "../pages/pipeline/reducer";

const hooks = vi.hoisted(() => ({ config: vi.fn() }));
vi.mock("../api/queries", () => ({ useDemoConfig: hooks.config }));
const event = (
  index: number,
  overrides: Partial<DecisionEvent> = {},
): DecisionEvent => ({
  seq: index,
  timestamp: "2026-09-27T00:00:04Z",
  run_id: "run",
  fixture_id: "fixture",
  module: "quality",
  resource_reference: `Patient/${index}`,
  decision: "auto_accept",
  confidence: 0.8,
  lane: "review",
  lane_reason: "score 60 < threshold 70",
  latency_ms: 3,
  jev_latency_ms: index,
  tokens_used: 2,
  ground_truth_match: true,
  error: null,
  ...overrides,
});
const summary = (review = 0): RunSummary => ({
  runId: "run",
  total: 15,
  processed: 15,
  status: "finished",
  lanes: { auto_accepted: 0, routed: 0, flagged: 0, review },
  routedByCategory: {},
  agreement: { correct: 8, judged: 10 },
  tokens: 1_000_000_000,
  errors: 0,
});

describe("Pipeline components", () => {
  it("`RerunDelta` shows the sign.", () => {
    const { rerender } = render(
      <RerunDelta previous={summary(2)} current={summary(5)} />,
    );
    expect(screen.getByTestId("rerun-delta")).toHaveTextContent("Δ +3");
    rerender(<RerunDelta previous={summary(5)} current={summary(2)} />);
    expect(screen.getByTestId("rerun-delta")).toHaveTextContent("Δ −3");
    rerender(<RerunDelta previous={summary(2)} current={summary(2)} />);
    expect(screen.getByTestId("rerun-delta")).toHaveTextContent("Δ ±0");
    rerender(<RerunDelta previous={null} current={summary(2)} />);
    expect(screen.queryByTestId("rerun-delta")).toBeNull();
  });

  it("LiveFeed renders exactly 100 rows and links to Studio", () => {
    const events = Array.from({ length: 500 }, (_, index) => event(index));
    function Location() {
      return (
        <output data-testid="location">
          {useLocation().pathname}
          {useLocation().search}
        </output>
      );
    }
    render(
      <MemoryRouter>
        <LiveFeed events={events} />
        <Routes>
          <Route path="*" element={<Location />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(
      screen.getByTestId("live-feed").querySelectorAll("tbody tr"),
    ).toHaveLength(100);
    fireEvent.click(screen.getAllByRole("row")[1]);
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/studio/quality?fixture=fixture",
    );
  });

  it("StatsStrip shows nearest-rank percentiles, agreement, throughput, and live cost", () => {
    const current = summary();
    const events = [
      ...Array.from({ length: 10 }, (_, i) =>
        event(i, { timestamp: `2026-09-27T00:00:0${4 - (i % 5)}Z` }),
      ),
      ...Array.from({ length: 5 }, (_, i) =>
        event(i + 20, { timestamp: "2026-09-26T23:59:00Z" }),
      ),
    ];
    const state: PipelineState = {
      ...initialPipelineState,
      current,
      events,
      latencies: [1, 2, 3, 4, 5],
      confidences: [],
    };
    const { rerender } = render(<StatsStrip state={state} live={false} />);
    expect(screen.getByTestId("stats-strip")).toHaveTextContent(
      "Throughput 2.0/s",
    );
    expect(screen.getByTestId("stats-strip")).toHaveTextContent("p50 3 ms");
    expect(screen.getByTestId("stats-strip")).toHaveTextContent("p95 5 ms");
    expect(screen.getByTestId("stats-strip")).toHaveTextContent(
      "Agreement 80%",
    );
    expect(screen.queryByTestId("cost")).toBeNull();
    rerender(<StatsStrip state={state} live />);
    expect(screen.getByTestId("cost")).toHaveTextContent("$42.000000");
    rerender(
      <StatsStrip
        state={{
          ...state,
          current: { ...current, agreement: { correct: 0, judged: 0 } },
        }}
        live
      />,
    );
    expect(screen.getByTestId("stats-strip")).toHaveTextContent("Agreement —");
  });

  it("ReviewQueue shows exact reasons and simulated actions make no fetch", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<ReviewQueue events={[event(1)]} />);
    await user.click(screen.getByRole("button", { name: /Patient\/1/ }));
    expect(screen.getByTestId("review-reason")).toHaveTextContent(
      "score 60 < threshold 70",
    );
    await user.click(screen.getByRole("button", { name: "Accept" }));
    expect(screen.getByText("accepted")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Override" }));
    expect(screen.getByText("overridden")).toBeVisible();
    expect(screen.getByText("simulated reviewer")).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("RunControls posts source, pace, modules and stops the current run", async () => {
    const user = userEvent.setup();
    hooks.config.mockReturnValue({
      data: {
        thresholds: {
          quality_threshold: 70,
          route_confidence_minimum: 0.5,
          notifiable_review: 0.5,
          notifiable_confirmed: 0.8,
        },
      },
    });
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ run_id: "next", status: "started", total: 1 }),
          { status: 200 },
        ),
      );
    const running = { ...summary(), status: "running" as const };
    render(<RunControls current={running} onReset={vi.fn()} />);
    expect(screen.getByText("Quality")).toBeVisible();
    expect(screen.getByText("Router")).toBeVisible();
    expect(screen.getByText("Notifiable")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Source"), "hard");
    await user.selectOptions(screen.getByLabelText("Pace"), "max");
    await user.click(screen.getByRole("button", { name: "Start" }));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      source: "hard",
      rate_per_s: null,
      modules: ["quality", "router", "notifiable"],
    });
    await user.selectOptions(screen.getByLabelText("Pace"), "1");
    await user.click(screen.getByRole("button", { name: "Start" }));
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toMatchObject({
      rate_per_s: 1,
    });
    await user.click(screen.getByRole("button", { name: "Stop" }));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/v1/demo/pipeline/run/stop");
    fetchMock.mockRestore();
  });
});
