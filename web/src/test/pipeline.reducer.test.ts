import { describe, expect, it } from "vitest";
import type { StreamEvent } from "../api/sse";
import {
  initialPipelineState,
  pipelineReducer,
} from "../pages/pipeline/reducer";

function run(
  status: "started" | "finished" | "stopped",
  id = "run-1",
): StreamEvent {
  return {
    kind: "run",
    seq: 1,
    data: { run_id: id, status, total: 600, processed: 2 },
  };
}
function decision(index: number, runId = "run-1"): StreamEvent {
  return {
    kind: "decision",
    seq: index + 2,
    data: {
      seq: index + 2,
      timestamp: "2026-09-27T00:00:00Z",
      run_id: runId,
      fixture_id: "fixture.json",
      module: "router",
      resource_reference: "Bundle/test",
      decision: "lab_result",
      confidence: 0.9,
      lane: "routed",
      lane_reason: "lab_result ≥ 0.82",
      latency_ms: 2,
      jev_latency_ms: index,
      tokens_used: 3,
      ground_truth_match: true,
      error: null,
    },
  };
}
describe("pipelineReducer", () => {
  const contractTitle = [
    "`started` → decisions → `finished`; lane counts sum to `processed`; foreign `run_id` ignored;",
    " `previous` kept on a new start; the event cap is 500.",
  ].join("");
  it(contractTitle, () => {
    let state = pipelineReducer(initialPipelineState, {
      type: "event",
      event: run("started"),
    });
    state = pipelineReducer(state, { type: "event", event: decision(1) });
    state = pipelineReducer(state, {
      type: "event",
      event: decision(2, "foreign"),
    });
    state = pipelineReducer(state, { type: "event", event: run("finished") });
    expect(state.current?.processed).toBe(2);
    expect(
      Object.values(state.current?.lanes ?? {}).reduce(
        (left, right) => left + right,
        0,
      ),
    ).toBe(1);
    state = pipelineReducer(state, {
      type: "event",
      event: run("started", "new"),
    });
    expect(state.previous?.runId).toBe("run-1");
  });
  it("`started` → decisions → `finished`; lane counts sum to `processed`", () => {
    let state = pipelineReducer(initialPipelineState, {
      type: "event",
      event: run("started"),
    });
    state = pipelineReducer(state, { type: "event", event: decision(1) });
    state = pipelineReducer(state, { type: "event", event: run("finished") });
    expect(state.current?.status).toBe("finished");
    expect(
      Object.values(state.current?.lanes ?? {}).reduce((a, b) => a + b, 0),
    ).toBe(1);
    expect(state.current?.routedByCategory.lab_result).toBe(1);
    expect(state.current?.agreement).toEqual({ correct: 1, judged: 1 });
  });
  it("foreign `run_id` ignored; `previous` kept on a new start", () => {
    let state = pipelineReducer(initialPipelineState, {
      type: "event",
      event: run("started"),
    });
    state = pipelineReducer(state, {
      type: "event",
      event: decision(1, "other"),
    });
    state = pipelineReducer(state, {
      type: "event",
      event: run("started", "run-2"),
    });
    expect(state.current?.runId).toBe("run-2");
    expect(state.previous?.runId).toBe("run-1");
    expect(state.events).toHaveLength(0);
  });
  it("the event cap is 500 and latencies keep the last 50", () => {
    let state = pipelineReducer(initialPipelineState, {
      type: "event",
      event: run("started"),
    });
    for (let index = 0; index < 501; index += 1)
      state = pipelineReducer(state, { type: "event", event: decision(index) });
    expect(state.events).toHaveLength(500);
    expect(state.latencies).toEqual(
      Array.from({ length: 50 }, (_, index) => index + 451),
    );
  });
});
